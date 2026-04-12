using Finadoc.Web.Data;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Workers;

/// <summary>
/// Runs daily, deletes Documents and Analyses rows where ExpiresAt &lt;= now,
/// and removes the corresponding files from disk.
/// Also purges AuditEvents older than 90 days.
/// Full implementation in P8.
/// </summary>
public class RetentionCleanupWorker(IServiceScopeFactory scopeFactory, ILogger<RetentionCleanupWorker> logger)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            logger.LogInformation("RetentionCleanupWorker tick — full implementation in P8.");
            // TODO (P8): delete expired rows and files, log audit events
            await Task.Delay(TimeSpan.FromHours(24), stoppingToken);
        }
    }
}
