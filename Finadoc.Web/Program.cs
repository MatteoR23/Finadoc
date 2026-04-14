using Finadoc.Web.Auth;
using Finadoc.Web.Data;
using Finadoc.Web.Services;
using Finadoc.Web.Workers;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Blazor Server
builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor();

// EF Core + SQLite
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));

// Cookie authentication — HttpOnly, SameSite=Strict, 8-hour sliding expiration
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.Cookie.Name = "finadoc.auth";
        options.Cookie.HttpOnly = true;
        options.Cookie.SecurePolicy = CookieSecurePolicy.SameAsRequest; // HTTP in Docker POC
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

// Application services
builder.Services.AddScoped<AuditService>();
builder.Services.AddScoped<UserService>();
builder.Services.AddScoped<AnalysisService>();

// Background workers
builder.Services.AddHostedService<RetentionCleanupWorker>();

// HttpClient for AI service
builder.Services.AddHttpClient("AiService", client =>
{
    var baseUrl = builder.Configuration["AiService:BaseUrl"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromMinutes(5);
});

var app = builder.Build();

// Auto-apply EF Core migrations on startup (idempotent — safe with shared Docker volume)
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
// Runs before UseAuthentication so it works even before any user is created.
app.Use(async (context, next) =>
{
    var path = context.Request.Path.Value ?? "";
    var skip = path.StartsWith("/setup", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/_", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/css", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/js", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/lib", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/favicon", StringComparison.OrdinalIgnoreCase);

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
