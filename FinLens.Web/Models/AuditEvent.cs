namespace FinLens.Web.Models;

public class AuditEvent
{
    public long Id { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public Guid? UserId { get; set; }
    /// <summary>E.g. "login", "document_upload", "analysis_started", "pdf_downloaded",
    /// "document_deleted", "user_created", "user_deactivated", "group_assigned".</summary>
    public string Action { get; set; } = string.Empty;
    /// <summary>E.g. "Document", "Analysis", "User"</summary>
    public string? TargetType { get; set; }
    public string? TargetId { get; set; }
    /// <summary>"success" or "failure"</summary>
    public string Outcome { get; set; } = "success";
    /// <summary>JSON blob with additional context.</summary>
    public string? Details { get; set; }
}
