using System.Text;
using System.Text.RegularExpressions;
using Finadoc.Web.Data;
using Finadoc.Web.Models;
using Finadoc.Web.Services.Storage;
using Microsoft.AspNetCore.Components.Forms;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Services;

public class DocumentService(
    AppDbContext db,
    AuditService audit,
    IStorageService storage,
    IConfiguration config,
    ILogger<DocumentService> logger)
{
    private const int MaxPdfPages = 10;
    private const long MaxFileSizeBytes = 20 * 1024 * 1024; // 20 MB
    private readonly string _documentsBucket = config["Storage:DocumentsBucket"] ?? "finadoc-documents";

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
        var storageKey = $"documents/{docId}/{file.Name}";
        var contentType = ext == ".pdf" ? "application/pdf"
            : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

        await using var uploadStream = new MemoryStream(bytes);
        await storage.UploadAsync(_documentsBucket, storageKey, uploadStream, contentType);

        var doc = new Document
        {
            Id = docId,
            UserId = userId,
            OriginalFileName = file.Name,
            StorageKey = storageKey,
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

    public async Task<List<Document>> GetByUserAsync(Guid userId)
        => await db.Documents
            .Where(d => d.UserId == userId)
            .OrderByDescending(d => d.UploadedAt)
            .Take(50)
            .ToListAsync();

    public async Task<string?> DeleteAsync(Guid docId, Guid userId)
    {
        var doc = await db.Documents.FindAsync(docId);
        if (doc is null || doc.UserId != userId)
            return "Document not found.";

        try
        {
            await storage.DeletePrefixAsync(_documentsBucket, $"documents/{docId}/");
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Could not delete S3 objects for document {Id}", docId);
        }

        db.Documents.Remove(doc);
        await db.SaveChangesAsync();

        await audit.LogAsync("document_deleted", userId, "Document", docId.ToString(), "success",
            $$"""{"file":"{{EscapeJson(doc.OriginalFileName)}}"}""");

        logger.LogInformation("Document {Id} deleted by user {UserId}", docId, userId);
        return null;
    }

    private static int CountPdfPages(byte[] bytes)
    {
        var text = Encoding.Latin1.GetString(bytes);
        return Regex.Matches(text, @"/Type\s*/Page(?!s)").Count;
    }

    private static string EscapeJson(string v) =>
        v.Replace("\\", "\\\\").Replace("\"", "\\\"");
}
