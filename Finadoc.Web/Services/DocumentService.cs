using System.Text;
using System.Text.RegularExpressions;
using Finadoc.Web.Data;
using Finadoc.Web.Models;
using Microsoft.AspNetCore.Components.Forms;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Services;

public class DocumentService(
    AppDbContext db,
    AuditService audit,
    IConfiguration config,
    ILogger<DocumentService> logger)
{
    private const int MaxPdfPages = 10;
    private const long MaxFileSizeBytes = 20 * 1024 * 1024; // 20 MB
    private readonly string _dataDir = config["Storage:DataDir"] ?? "/data";

    /// <summary>
    /// Validates and stores an uploaded file, creates the DB record, and logs the audit event.
    /// </summary>
    public async Task<(Document? Doc, string? Error)> SaveAsync(IBrowserFile file, Guid userId)
    {
        var ext = Path.GetExtension(file.Name).ToLowerInvariant();
        if (ext != ".pdf" && ext != ".xlsx")
            return (null, "Only .pdf and .xlsx files are accepted.");

        byte[] bytes;
        try
        {
            await using var stream = file.OpenReadStream(MaxFileSizeBytes);
            using var ms = new MemoryStream();
            await stream.CopyToAsync(ms);
            bytes = ms.ToArray();
        }
        catch (IOException)
        {
            return (null, $"File exceeds the {MaxFileSizeBytes / 1024 / 1024} MB size limit.");
        }

        if (ext == ".pdf")
        {
            var pages = CountPdfPages(bytes);
            if (pages > MaxPdfPages)
            {
                await audit.LogAsync("document_upload", userId, "Document", null, "failure",
                    $$"""{"reason":"too_many_pages","pages":{{pages}},"file":"{{EscapeJson(file.Name)}}"}""");
                return (null, $"The PDF has {pages} pages. Maximum allowed is {MaxPdfPages}.");
            }
        }

        var docId = Guid.NewGuid();
        var uploadDir = Path.Combine(_dataDir, "uploads", docId.ToString());
        Directory.CreateDirectory(uploadDir);
        var filePath = Path.Combine(uploadDir, file.Name);
        await File.WriteAllBytesAsync(filePath, bytes);

        var doc = new Document
        {
            Id = docId,
            UserId = userId,
            OriginalFileName = file.Name,
            StoragePath = filePath,
            Format = ext.TrimStart('.'),
            UploadedAt = DateTime.UtcNow,
            ExpiresAt = DateTime.UtcNow.AddDays(90),
        };
        db.Documents.Add(doc);
        await db.SaveChangesAsync();

        await audit.LogAsync("document_upload", userId, "Document", docId.ToString(), "success",
            $$"""{"file":"{{EscapeJson(file.Name)}}","format":"{{doc.Format}}"}""");

        logger.LogInformation("Document {Id} saved by user {UserId}: {FileName}", docId, userId, file.Name);
        return (doc, null);
    }

    /// <summary>Returns the user's documents ordered by most recent, capped at 50.</summary>
    public async Task<List<Document>> GetByUserAsync(Guid userId)
        => await db.Documents
            .Where(d => d.UserId == userId)
            .OrderByDescending(d => d.UploadedAt)
            .Take(50)
            .ToListAsync();

    // Each page object in a PDF has /Type /Page (not /Pages which is the tree root).
    // Decoding as Latin-1 keeps byte values intact for binary PDF content.
    private static int CountPdfPages(byte[] bytes)
    {
        var text = Encoding.Latin1.GetString(bytes);
        return Regex.Matches(text, @"/Type\s*/Page(?!s)").Count;
    }

    private static string EscapeJson(string v) =>
        v.Replace("\\", "\\\\").Replace("\"", "\\\"");
}
