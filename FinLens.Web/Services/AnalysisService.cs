using FinLens.Web.Data;
using FinLens.Web.Jobs;
using FinLens.Web.Models;
using Hangfire;
using Microsoft.EntityFrameworkCore;

namespace FinLens.Web.Services;

public class AnalysisService(AppDbContext db, IBackgroundJobClient jobs)
{
    public async Task<Analysis> StartAnalysisAsync(
        Guid documentId,
        string groupContext,
        Guid userId,
        string mode = "Standard",
        string? goal = null)
    {
        var doc = await db.Documents.FindAsync(documentId)
            ?? throw new InvalidOperationException("Document not found.");

        mode = string.Equals(mode, "Agentic", StringComparison.OrdinalIgnoreCase)
            ? "Agentic"
            : "Standard";

        if (mode == "Standard" && string.IsNullOrWhiteSpace(groupContext))
            throw new InvalidOperationException("A group context is required for standard analyses.");

        var analysis = new Analysis
        {
            DocumentId = doc.Id,
            Mode = mode,
            Goal = string.IsNullOrWhiteSpace(goal) ? null : goal.Trim(),
            GroupContext = groupContext,
            Status = "Queued",
            ExpiresAt = DateTime.UtcNow.AddDays(90),
        };
        db.Analyses.Add(analysis);
        await db.SaveChangesAsync();

        jobs.Enqueue<AnalysisJob>(j => j.RunAsync(analysis.Id, userId));
        return analysis;
    }

    public async Task<List<Analysis>> GetByUserAsync(Guid userId) =>
        await db.Analyses
            .Include(a => a.Document)
            .Where(a => a.Document.UserId == userId)
            .OrderByDescending(a => a.StartedAt)
            .AsNoTracking()
            .ToListAsync();

    public async Task<Dictionary<Guid, Analysis?>> GetLatestByDocumentIdsAsync(IEnumerable<Guid> docIds)
    {
        var ids = docIds.ToList();
        var analyses = await db.Analyses
            .Where(a => ids.Contains(a.DocumentId))
            .OrderByDescending(a => a.StartedAt)
            .AsNoTracking()
            .ToListAsync();

        return analyses
            .GroupBy(a => a.DocumentId)
            .ToDictionary(g => g.Key, g => (Analysis?)g.First());
    }
}
