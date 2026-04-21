using Amazon.S3;
using Finadoc.Web.Auth;
using Finadoc.Web.Data;
using Finadoc.Web.Hubs;
using Finadoc.Web.Jobs;
using Finadoc.Web.Services;
using Finadoc.Web.Services.Storage;
using Finadoc.Web.Workers;
using Hangfire;
using Hangfire.PostgreSql;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Data Protection — persist keys to the shared volume so cookies survive restarts.
var keysPath = builder.Configuration["DataProtection:KeysPath"] ?? "/data/keys";
builder.Services.AddDataProtection()
    .PersistKeysToFileSystem(new DirectoryInfo(keysPath))
    .SetApplicationName("Finadoc");

// Blazor Server
builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor(options =>
{
    options.DetailedErrors = builder.Environment.IsDevelopment();
});

// EF Core + PostgreSQL
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// Cookie authentication — HttpOnly, SameSite=Strict, 8-hour sliding expiration
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.Cookie.Name = "finadoc.auth";
        options.Cookie.HttpOnly = true;
        options.Cookie.SecurePolicy = CookieSecurePolicy.SameAsRequest;
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.ExpireTimeSpan = TimeSpan.FromHours(8);
        options.SlidingExpiration = true;
        options.LoginPath = "/login";
        options.LogoutPath = "/logout";
    });

// Authorization policies
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("AdminOnly", policy => policy.RequireClaim("IsAdmin", "true"));
});

// HTTP context accessor — required by CookieAuthStateProvider
builder.Services.AddHttpContextAccessor();

// Blazor auth state bridge
builder.Services.AddScoped<AuthenticationStateProvider, CookieAuthStateProvider>();
builder.Services.AddCascadingAuthenticationState();

// Auth provider (Local or Ldaps, configured in appsettings.json)
var authProvider = builder.Configuration["Auth:Provider"] ?? "Local";
if (authProvider == "Ldaps")
    builder.Services.AddScoped<IAuthProvider, LdapsAuthProvider>();
else
    builder.Services.AddScoped<IAuthProvider, LocalAuthProvider>();

// Object storage (MinIO / S3)
var storageSettings = builder.Configuration.GetSection("Storage").Get<StorageSettings>()
    ?? new StorageSettings();
builder.Services.AddSingleton(storageSettings);
builder.Services.AddSingleton<IAmazonS3>(_ =>
{
    var s3Config = new AmazonS3Config { ForcePathStyle = storageSettings.Provider == "minio" };
    if (!string.IsNullOrWhiteSpace(storageSettings.Endpoint))
        s3Config.ServiceURL = storageSettings.Endpoint;
    else
        s3Config.RegionEndpoint = Amazon.RegionEndpoint.GetBySystemName(storageSettings.Region);
    return new AmazonS3Client(storageSettings.AccessKey, storageSettings.SecretKey, s3Config);
});
builder.Services.AddScoped<IStorageService, S3StorageService>();

// SignalR (in-memory backplane for single instance; add .AddStackExchangeRedis(...) for multi-instance)
builder.Services.AddSignalR();

// Hangfire — PostgreSQL-backed job queue; scales horizontally by adding worker instances
var hangfireConnStr = builder.Configuration.GetConnectionString("DefaultConnection")!;
builder.Services.AddHangfire(c => c
    .SetDataCompatibilityLevel(CompatibilityLevel.Version_180)
    .UseSimpleAssemblyNameTypeSerializer()
    .UseRecommendedSerializerSettings()
    .UsePostgreSqlStorage(o => o.UseNpgsqlConnection(hangfireConnStr)));
builder.Services.AddHangfireServer(options =>
{
    options.WorkerCount = Environment.ProcessorCount * 2;
});

// Application services
builder.Services.AddScoped<AuditService>();
builder.Services.AddScoped<UserService>();
builder.Services.AddScoped<DocumentService>();
builder.Services.AddScoped<AnalysisService>();

// Job handlers (Hangfire resolves these via DI)
builder.Services.AddScoped<AnalysisJob>();

// Background workers
builder.Services.AddHostedService<RetentionCleanupWorker>();

// HttpClient for AI service
var internalApiKey = builder.Configuration["AiService:InternalApiKey"];
if (string.IsNullOrWhiteSpace(internalApiKey))
    throw new InvalidOperationException("AiService:InternalApiKey is not configured. Set AiService__InternalApiKey in environment.");

builder.Services.AddHttpClient("AiService", client =>
{
    var baseUrl = builder.Configuration["AiService:BaseUrl"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromMinutes(5);
    client.DefaultRequestHeaders.Add("X-Internal-Api-Key", internalApiKey);
});

var app = builder.Build();

// Auto-apply EF Core migrations on startup (idempotent)
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.Migrate();
}

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
}

app.UseStaticFiles();

// First-run guard: redirect all traffic to /setup if no users exist yet.
app.Use(async (context, next) =>
{
    var path = context.Request.Path.Value ?? "";
    var skip = path.StartsWith("/setup", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/hangfire", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/_", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/css", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/js", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/lib", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/favicon", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/hubs", StringComparison.OrdinalIgnoreCase);

    if (!skip)
    {
        using var scope = context.RequestServices.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        if (!await db.Users.AnyAsync())
        {
            context.Response.Redirect("/setup");
            return;
        }
    }

    await next();
});

app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();

app.MapRazorPages();
app.MapBlazorHub();
app.MapHub<AnalysisHub>("/hubs/analysis");
app.UseHangfireDashboard("/hangfire", new DashboardOptions
{
    Authorization = [new HangfireAdminAuthFilter()],
    DashboardTitle = "Finadoc — Job Queue",
});
app.MapFallbackToPage("/_Host");

// Health check: call Python AI service on startup and log the result
await CheckAiServiceHealthAsync(app);

app.Run();


static async Task CheckAiServiceHealthAsync(WebApplication app)
{
    var logger = app.Services.GetRequiredService<ILogger<Program>>();
    try
    {
        var factory = app.Services.GetRequiredService<IHttpClientFactory>();
        var client = factory.CreateClient("AiService");
        var response = await client.GetAsync("/health");
        if (response.IsSuccessStatusCode)
            logger.LogInformation("AI service health check passed.");
        else
            logger.LogWarning("AI service health check returned {StatusCode}.", response.StatusCode);
    }
    catch (Exception ex)
    {
        logger.LogWarning(ex, "AI service health check failed — service may not be running yet.");
    }
}
