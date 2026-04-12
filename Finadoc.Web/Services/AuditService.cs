using Finadoc.Web.Data;
using Finadoc.Web.Models;

namespace Finadoc.Web.Services;

/// <summary>
/// Writes append-only audit events to the database.
/// Full implementation in P8; basic logging calls are placed throughout the app from P2 onwards.
/// </summary>
public class AuditService(AppDbContext db)
{
    public async Task LogAsync(
        string action,
        Guid? userId = null,
        string? targetType = null,
        string? targetId = null,
        string outcome = "success",
        string? details = null)
    {
        db.AuditEvents.Add(new AuditEvent
        {
            Action = action,
            UserId = userId,
            TargetType = targetType,
            TargetId = targetId,
            Outcome = outcome,
            Details = details,
        });
        await db.SaveChangesAsync();
    }
}
