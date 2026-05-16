namespace FinLens.Web.Models;

public class Analysis
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid DocumentId { get; set; }
    public Document Document { get; set; } = null!;

    /// <summary>"Standard" or "Agentic".</summary>
    public string Mode { get; set; } = "Standard";
    /// <summary>Optional user goal for agentic planning.</summary>
    public string? Goal { get; set; }
    /// <summary>"PM", "RM", "DQ", or "Regulatory"</summary>
    public string GroupContext { get; set; } = string.Empty;
    /// <summary>"Pending", "Running", "Completed", "Failed"</summary>
    public string Status { get; set; } = "Pending";
    /// <summary>"ingesting", "analyzing", "generating" — null when not Running.</summary>
    public string? Step { get; set; }
    /// <summary>Absolute path to the generated report.pdf on the shared volume.</summary>
    public string? PdfPath { get; set; }
    public string? ResultS3Key { get; set; }
    public string? ReportS3Key { get; set; }
    public string? PlanS3Key { get; set; }
    public string? TraceS3Key { get; set; }
    public DateTime StartedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    /// <summary>Set to StartedAt + 90 days.</summary>
    public DateTime ExpiresAt { get; set; }
}
