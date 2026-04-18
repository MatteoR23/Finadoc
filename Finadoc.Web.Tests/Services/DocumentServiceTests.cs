using System.Text;
using Finadoc.Web.Data;
using Finadoc.Web.Models;
using Finadoc.Web.Services;
using Finadoc.Web.Services.Storage;
using Microsoft.AspNetCore.Components.Forms;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;

namespace Finadoc.Web.Tests.Services;

public class DocumentServiceTests : IDisposable
{
    private readonly string _dataDir;
    private readonly AppDbContext _db;
    private readonly FakeStorageService _storage;
    private readonly DocumentService _service;
    private readonly Guid _userId = Guid.NewGuid();

    public DocumentServiceTests()
    {
        _dataDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
        Directory.CreateDirectory(_dataDir);

        _db = new AppDbContext(new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options);

        var audit = new AuditService(_db);
        var config = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { ["Storage:DataDir"] = _dataDir })
            .Build();

        _storage = new FakeStorageService();
        _service = new DocumentService(_db, audit, _storage, config, NullLogger<DocumentService>.Instance);
    }

    public void Dispose()
    {
        _db.Dispose();
        if (Directory.Exists(_dataDir))
            Directory.Delete(_dataDir, recursive: true);
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    // Produces bytes that decode to a Latin-1 string with the expected number of
    // /Type /Page entries (the signature used by DocumentService to count pages).
    private static byte[] MakePdfBytes(int pages)
    {
        var sb = new StringBuilder();
        sb.Append("%PDF-1.4\n");
        for (var i = 0; i < pages; i++)
            sb.Append("/Type /Page\n");
        return Encoding.Latin1.GetBytes(sb.ToString());
    }

    private static FakeBrowserFile PdfFile(string name, int pages) =>
        new(name, MakePdfBytes(pages));

    private static FakeBrowserFile XlsxFile(string name = "report.xlsx") =>
        new(name, [0x50, 0x4B, 0x03, 0x04]); // XLSX magic bytes (ZIP)

    // ── SaveAsync — extension validation ─────────────────────────────────────

    [Fact]
    public async Task SaveAsync_RejectsUnsupportedExtension()
    {
        var file = new FakeBrowserFile("document.txt", "hello"u8.ToArray());

        var (doc, error) = await _service.SaveAsync(file, _userId);

        Assert.Null(doc);
        Assert.NotNull(error);
        Assert.Empty(_db.Documents);
    }

    [Fact]
    public async Task SaveAsync_AcceptsPdfExtension()
    {
        var (doc, error) = await _service.SaveAsync(PdfFile("ok.pdf", 5), _userId);

        Assert.Null(error);
        Assert.NotNull(doc);
    }

    [Fact]
    public async Task SaveAsync_AcceptsXlsxExtension()
    {
        var (doc, error) = await _service.SaveAsync(XlsxFile(), _userId);

        Assert.Null(error);
        Assert.NotNull(doc);
    }

    // ── SaveAsync — oversize file ─────────────────────────────────────────────

    [Fact]
    public async Task SaveAsync_RejectsOversizedFile()
    {
        var file = new FakeBrowserFile("big.pdf", [], throwOnRead: true);

        var (doc, error) = await _service.SaveAsync(file, _userId);

        Assert.Null(doc);
        Assert.NotNull(error);
        Assert.Empty(_db.Documents);
    }

    // ── SaveAsync — PDF page limit ────────────────────────────────────────────

    [Fact]
    public async Task SaveAsync_RejectsPdf_WithMoreThanTenPages()
    {
        var (doc, error) = await _service.SaveAsync(PdfFile("long.pdf", 11), _userId);

        Assert.Null(doc);
        Assert.NotNull(error);
        Assert.Empty(_db.Documents);
    }

    [Fact]
    public async Task SaveAsync_RejectsPdf_WithMoreThanTenPages_LogsFailureAuditEvent()
    {
        await _service.SaveAsync(PdfFile("long.pdf", 11), _userId);

        var evt = _db.AuditEvents.Single();
        Assert.Equal("document_upload", evt.Action);
        Assert.Equal("failure", evt.Outcome);
    }

    [Theory]
    [InlineData(1)]
    [InlineData(10)]
    public async Task SaveAsync_AcceptsPdf_UpToTenPages(int pages)
    {
        var (doc, error) = await _service.SaveAsync(PdfFile($"ok_{pages}p.pdf", pages), _userId);

        Assert.Null(error);
        Assert.NotNull(doc);
    }

    // ── SaveAsync — DB record and audit ───────────────────────────────────────

    [Fact]
    public async Task SaveAsync_CreatesDocumentRecord()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 3), _userId);

        Assert.NotNull(doc);
        var stored = _db.Documents.Single();
        Assert.Equal(doc!.Id, stored.Id);
        Assert.Equal(_userId, stored.UserId);
        Assert.Equal("report.pdf", stored.OriginalFileName);
        Assert.Equal("pdf", stored.Format);
    }

    [Fact]
    public async Task SaveAsync_SetsExpiresAt_NinetyDaysFromNow()
    {
        var before = DateTime.UtcNow.AddDays(89);

        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 3), _userId);

        var after = DateTime.UtcNow.AddDays(91);
        Assert.True(doc!.ExpiresAt > before);
        Assert.True(doc.ExpiresAt < after);
    }

    [Fact]
    public async Task SaveAsync_LogsSuccessAuditEvent()
    {
        await _service.SaveAsync(PdfFile("report.pdf", 3), _userId);

        var evt = _db.AuditEvents.Single();
        Assert.Equal("document_upload", evt.Action);
        Assert.Equal("success", evt.Outcome);
        Assert.Equal(_userId, evt.UserId);
    }

    [Fact]
    public async Task SaveAsync_UploadsFileToStorage()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 3), _userId);

        Assert.Equal("finadoc-documents", _storage.Bucket);
        Assert.NotNull(_storage.Key);
        Assert.StartsWith($"documents/{doc!.Id}/", _storage.Key);
        Assert.Equal("application/pdf", _storage.ContentType);
        Assert.NotNull(_storage.ContentBytes);
        Assert.True(_storage.ContentBytes.Length > 0);
    }

    // ── GetByUserAsync ────────────────────────────────────────────────────────

    [Fact]
    public async Task GetByUserAsync_ReturnsOnlyOwnerDocuments()
    {
        var otherId = Guid.NewGuid();
        await _service.SaveAsync(PdfFile("mine.pdf", 1), _userId);
        await _service.SaveAsync(PdfFile("theirs.pdf", 1), otherId);

        var results = await _service.GetByUserAsync(_userId);

        Assert.Single(results);
        Assert.Equal("mine.pdf", results[0].OriginalFileName);
    }

    [Fact]
    public async Task GetByUserAsync_ReturnsDocumentsOrderedByUploadedAtDescending()
    {
        // Insert two documents directly so we can control UploadedAt precisely.
        _db.Documents.AddRange(
            new Document
            {
                UserId = _userId,
                OriginalFileName = "old.pdf",
                Format = "pdf",
                UploadedAt = DateTime.UtcNow.AddMinutes(-10),
                ExpiresAt = DateTime.UtcNow.AddDays(90),
            },
            new Document
            {
                UserId = _userId,
                OriginalFileName = "new.pdf",
                Format = "pdf",
                UploadedAt = DateTime.UtcNow,
                ExpiresAt = DateTime.UtcNow.AddDays(90),
            });
        await _db.SaveChangesAsync();

        var results = await _service.GetByUserAsync(_userId);

        Assert.Equal("new.pdf", results[0].OriginalFileName);
        Assert.Equal("old.pdf", results[1].OriginalFileName);
    }

    // ── DeleteAsync ───────────────────────────────────────────────────────────

    [Fact]
    public async Task DeleteAsync_ReturnsError_WhenDocumentNotFound()
    {
        var error = await _service.DeleteAsync(Guid.NewGuid(), _userId);

        Assert.NotNull(error);
    }

    [Fact]
    public async Task DeleteAsync_ReturnsError_WhenDocumentBelongsToDifferentUser()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 2), _userId);

        var error = await _service.DeleteAsync(doc!.Id, Guid.NewGuid());

        Assert.NotNull(error);
        Assert.Single(_db.Documents); // record must still exist
    }

    [Fact]
    public async Task DeleteAsync_RemovesDbRecord()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 2), _userId);
        _db.AuditEvents.RemoveRange(_db.AuditEvents); // clear upload event
        await _db.SaveChangesAsync();

        await _service.DeleteAsync(doc!.Id, _userId);

        Assert.Empty(_db.Documents);
    }

    [Fact]
    public async Task DeleteAsync_LogsAuditEvent()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 2), _userId);
        _db.AuditEvents.RemoveRange(_db.AuditEvents);
        await _db.SaveChangesAsync();

        await _service.DeleteAsync(doc!.Id, _userId);

        var evt = _db.AuditEvents.Single();
        Assert.Equal("document_deleted", evt.Action);
        Assert.Equal("success", evt.Outcome);
        Assert.Equal(_userId, evt.UserId);
    }

    [Fact]
    public async Task DeleteAsync_ReturnsNull_OnSuccess()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 2), _userId);

        var error = await _service.DeleteAsync(doc!.Id, _userId);

        Assert.Null(error);
    }

    // ── Test double ──────────────────────────────────────────────────────────

    [Fact]
    public async Task DeleteAsync_DeletesDbRecord_EvenIfStorageDeleteFails()
    {
        var (doc, _) = await _service.SaveAsync(PdfFile("report.pdf", 2), _userId);
        _storage.ThrowOnDeletePrefix = true;
        _db.AuditEvents.RemoveRange(_db.AuditEvents);
        await _db.SaveChangesAsync();

        var error = await _service.DeleteAsync(doc!.Id, _userId);

        Assert.Null(error);
        Assert.Empty(_db.Documents);
        var evt = _db.AuditEvents.Single();
        Assert.Equal("document_deleted", evt.Action);
        Assert.Equal("success", evt.Outcome);
    }

    // ── Test double ──────────────────────────────────────────────────────────

    private sealed class FakeStorageService : IStorageService
    {
        public string? Bucket { get; private set; }
        public string? Key { get; private set; }
        public string? ContentType { get; private set; }
        public byte[]? ContentBytes { get; private set; }
        public bool ThrowOnDeletePrefix { get; set; }

        public async Task UploadAsync(string bucket, string key, Stream content, string contentType, CancellationToken ct = default)
        {
            Bucket = bucket;
            Key = key;
            ContentType = contentType;
            await using var ms = new MemoryStream();
            await content.CopyToAsync(ms, ct);
            ContentBytes = ms.ToArray();
        }

        public Task<Stream> DownloadAsync(string bucket, string key, CancellationToken ct = default)
            => throw new NotImplementedException();

        public Task DeleteAsync(string bucket, string key, CancellationToken ct = default)
            => throw new NotImplementedException();

        public Task DeletePrefixAsync(string bucket, string prefix, CancellationToken ct = default)
        {
            if (ThrowOnDeletePrefix)
                throw new Exception("Simulated storage failure.");
            return Task.CompletedTask;
        }
    }

    private sealed class FakeBrowserFile(string name, byte[] content, bool throwOnRead = false) : IBrowserFile
    {
        public string Name { get; } = name;
        public DateTimeOffset LastModified => DateTimeOffset.UtcNow;
        public long Size { get; } = content.Length;
        public string ContentType => "application/octet-stream";

        public Stream OpenReadStream(long maxAllowedSize = 512_000, CancellationToken cancellationToken = default)
        {
            if (throwOnRead)
                throw new IOException("File exceeds the size limit.");
            return new MemoryStream(content);
        }
    }
}
