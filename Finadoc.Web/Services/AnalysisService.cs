using Finadoc.Web.Data;
using Finadoc.Web.Jobs;
using Finadoc.Web.Models;
using Hangfire;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Services;

public class AnalysisService(AppDbContext db, IBackgroundJobClient jobs)
{
    public async Task<Analysis> StartAnalysisAsync(Guid documentId, string groupContext, Guid userId)
    {
        var doc = await db.Documents.FindAsync(documentId)
            ?? throw new InvalidOperationException("Document not found.");

        var analysis = new Analysis
        {
            DocumentId = doc.Id,
            GroupContext = groupContext,
            Status = "Queued",
            ExpiresAt = DateTime.UtcNow.AddDays(90),
        };
        db.Analyses.Add(analysis);
        await db.SaveChangesAsync();

        jobs.Enqueue<AnalysisJob>(j => j.RunAsync(analysis.Id, userId, groupContext));
        return analysis;
    }

    public async Task<Dictionary<Guid, Analysis?>> GetLatestByDocumentIdsAsync(IEnumerable<Guid> docIds)
    {
        var ids = docIds.ToList();
        var analyses = await db.Analyses
            .Where(a => ids.Contains(a.DocumentId))
            .OrderByDescending(a => a.StartedAt)
            .ToListAsync();

        return analyses
            .GroupBy(a => a.DocumentId)
            .ToDictionary(g => g.Key, g => (Analysis?)g.First());
    }
}
