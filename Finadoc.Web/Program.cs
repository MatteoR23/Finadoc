using Finadoc.Web.Auth;
using Finadoc.Web.Data;
using Finadoc.Web.Services;
using Finadoc.Web.Workers;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Blazor Server
builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor();

// EF Core + SQLite
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));

// Auth provider (Local or Ldaps, configured in appsettings.json)
var authProvider = builder.Configuration["Auth:Provider"] ?? "Local";
if (authProvider == "Ldaps")
    builder.Services.AddScoped<IAuthProvider, LdapsAuthProvider>();
else
    builder.Services.AddScoped<IAuthProvider, LocalAuthProvider>();

// Application services
builder.Services.AddScoped<AuditService>();
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

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
}

app.UseStaticFiles();
app.UseRouting();

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
