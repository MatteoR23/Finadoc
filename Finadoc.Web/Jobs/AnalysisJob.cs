using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Finadoc.Web.Data;
using Finadoc.Web.Hubs;
using Finadoc.Web.Models;
using Finadoc.Web.Services;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Jobs;

public class AnalysisJob(
    AppDbContext db,
    IHttpClientFactory httpClientFactory,
    IHubContext<AnalysisHub> hub,
    AuditService audit,
    IConfiguration config,
    ILogger<AnalysisJob> logger)
{
    public async Task RunAsync(Guid analysisId, Guid userId, string groupContext)
    {
        var analysis = await db.Analyses
            .Include(a => a.Document)
            .FirstOrDefaultAsync(a => a.Id == analysisId);

        if (analysis is null)
        {
            logger.LogWarning("AnalysisJob: analysis {Id} not found", analysisId);
            return;
        }

        analysis.Status = "Running";
        await db.SaveChangesAsync();
        await NotifyAsync(userId, analysisId, "Running");

        try
        {
            var outputsBucket = config["Storage:OutputsBucket"] ?? "finadoc-outputs";
            var documentsBucket = config["Storage:DocumentsBucket"] ?? "finadoc-documents";

            var requestBody = new AiAnalyzeRequest(
                DocumentS3Key: analysis.Document.StorageKey,
                DocumentsBucket: documentsBucket,
                DocumentFormat: analysis.Document.Format,
                Language: analysis.Document.Language,
                OutputsBucket: outputsBucket,
                OutputS3Prefix: $"analyses/{analysisId}/",
                UserContext: new AiUserContext(userId.ToString(), [groupContext]));

            var client = httpClientFactory.CreateClient("AiService");
            var response = await client.PostAsJsonAsync($"/analyze/{groupContext.ToLower()}", requestBody);

            if (!response.IsSuccessStatusCode)
            {
                var detail = await response.Content.ReadAsStringAsync();
                logger.LogError("AI service returned {Status} for analysis {Id}: {Detail}", response.StatusCode, analysisId, detail);
                await FailAsync(analysis, userId, $"AI service error: {response.StatusCode}");
                return;
            }

            var result = await response.Content.ReadFromJsonAsync<AiAnalyzeResponse>();
            analysis.Status = "Completed";
            analysis.PdfPath = result?.ResultS3Key;
            analysis.CompletedAt = DateTime.UtcNow;
            await db.SaveChangesAsync();

            await audit.LogAsync("analysis_generated", userId, "Analysis", analysisId.ToString(), "success");
            await NotifyAsync(userId, analysisId, "Completed");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "AnalysisJob {Id} failed unexpectedly", analysisId);
            await FailAsync(analysis, userId, ex.Message);
            throw; // Let Hangfire retry with exponential backoff
        }
    }

    private async Task FailAsync(Analysis analysis, Guid userId, string reason)
    {
        analysis.Status = "Failed";
        analysis.CompletedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
        await audit.LogAsync("analysis_failed", userId, "Analysis", analysis.Id.ToString(), "failure",
            $"{{\"reason\":\"{EscapeJson(reason)}\"}}");
        await NotifyAsync(userId, analysis.Id, "Failed");
    }

    private Task NotifyAsync(Guid userId, Guid analysisId, string status)
        => hub.Clients.Group($"user-{userId}")
            .SendAsync("AnalysisUpdate", new { analysisId, status });

    private static string EscapeJson(string v) =>
        v.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");
}

internal record AiAnalyzeRequest(
    [property: JsonPropertyName("document_s3_key")] string DocumentS3Key,
    [property: JsonPropertyName("documents_bucket")] string DocumentsBucket,
    [property: JsonPropertyName("document_format")] string DocumentFormat,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("outputs_bucket")] string OutputsBucket,
    [property: JsonPropertyName("output_s3_prefix")] string OutputS3Prefix,
    [property: JsonPropertyName("user_context")] AiUserContext UserContext);

internal record AiUserContext(
    [property: JsonPropertyName("user_id")] string UserId,
    [property: JsonPropertyName("groups")] string[] Groups);

internal record AiAnalyzeResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("result_s3_key")] string? ResultS3Key,
    [property: JsonPropertyName("warnings")] List<string> Warnings);
