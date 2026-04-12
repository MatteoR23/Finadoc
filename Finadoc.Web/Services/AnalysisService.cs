using System.Net.Http.Json;
using Finadoc.Web.Data;
using Finadoc.Web.Models;

namespace Finadoc.Web.Services;

/// <summary>
/// Calls the Python AI service, stores results in SQLite, and notifies Blazor
/// components via SignalR (wired up in P4).
/// </summary>
public class AnalysisService(IHttpClientFactory httpClientFactory, AppDbContext db, ILogger<AnalysisService> logger)
{
    /// <summary>
    /// Submit a document for analysis.
    /// Full implementation in P4 (PM), P6 (RM), P7 (Regulatory).
    /// </summary>
    public async Task<Analysis> StartAnalysisAsync(Guid documentId, string groupContext, Guid userId)
    {
        // TODO (P4+): build request, POST to /analyze/{groupContext.ToLower()},
        // update Analysis record, trigger SignalR notification.
        throw new NotImplementedException($"Analysis pipeline not implemented yet for context '{groupContext}'.");
    }
}
