namespace Finadoc.Web.Models;

public class Document
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public User User { get; set; } = null!;

    public string OriginalFileName { get; set; } = string.Empty;
    /// <summary>Absolute path on the shared volume, e.g. /data/uploads/{Id}/{OriginalFileName}</summary>
    public string StoragePath { get; set; } = string.Empty;
    /// <summary>"pdf" or "xlsx"</summary>
    public string Format { get; set; } = string.Empty;
    /// <summary>"auto", "it", "en"</summary>
    public string Language { get; set; } = "auto";
    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;
    /// <summary>Set to UploadedAt + 90 days.</summary>
    public DateTime ExpiresAt { get; set; }

    public ICollection<Analysis> Analyses { get; set; } = [];
}
