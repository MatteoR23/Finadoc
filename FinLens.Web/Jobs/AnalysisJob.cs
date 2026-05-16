using System.Net.Http.Json;
using System.Text.Json.Serialization;
using FinLens.Web.Data;
using FinLens.Web.Hubs;
using FinLens.Web.Models;
using FinLens.Web.Services;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

namespace FinLens.Web.Jobs;

public class AnalysisJob(
    AppDbContext db,
    IHttpClientFactory httpClientFactory,
    IHubContext<AnalysisHub> hub,
    AnalysisProgressBroadcaster broadcaster,
    AuditService audit,
    IConfiguration config,
    ILogger<AnalysisJob> logger)
{
    public async Task RunAsync(Guid analysisId, Guid userId)
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
        analysis.Step = null;
        await db.SaveChangesAsync();
        await NotifyAsync(userId, analysisId, "Running", null);

        try
        {
            var groupContext = analysis.GroupContext;
            var outputsBucket = config["Storage:OutputsBucket"] ?? "finlens-outputs";
            var documentsBucket = config["Storage:DocumentsBucket"] ?? "finlens-documents";
            var appBaseUrl = config["App:BaseUrl"] ?? "http://localhost:8080";
            var callbackUrl = $"{appBaseUrl}/internal/analysis/{analysisId}/progress";
            var mode = string.Equals(analysis.Mode, "Agentic", StringComparison.OrdinalIgnoreCase)
                ? "Agentic"
                : "Standard";
            var allowedContexts = BuildAllowedContexts(groupContext);
            var userGroups = mode == "Agentic" ? allowedContexts : [groupContext];

            var requestBody = new AiAnalyzeRequest(
                DocumentS3Key: analysis.Document.StorageKey,
                DocumentsBucket: documentsBucket,
                DocumentFormat: analysis.Document.Format,
                Language: analysis.Document.Language,
                OutputsBucket: outputsBucket,
                OutputS3Prefix: $"analyses/{analysisId}/",
                UserContext: new AiUserContext(userId.ToString(), userGroups),
                AnalysisId: analysisId,
                CallbackUrl: callbackUrl,
                Agentic: mode == "Agentic"
                    ? new AiAgenticOptions(
                        Goal: analysis.Goal,
                        AllowedContexts: allowedContexts,
                        RequestedOutput: "pdf")
                    : null);

            var client = httpClientFactory.CreateClient("AiService");
            var targetPath = mode == "Agentic"
                ? "/analyze/agentic"
                : $"/analyze/{groupContext.ToLower()}";
            var response = await client.PostAsJsonAsync(targetPath, requestBody);

            if (!response.IsSuccessStatusCode)
            {
                var detail = await response.Content.ReadAsStringAsync();
                logger.LogError("AI service returned {Status} for analysis {Id}: {Detail}", response.StatusCode, analysisId, detail);
                await FailAsync(analysis, userId, $"AI service error: {response.StatusCode}");
                return;
            }

            var result = await response.Content.ReadFromJsonAsync<AiAnalyzeResponse>();
            analysis.Status = "Completed";
            analysis.Step = null;
            analysis.PdfPath = result?.ResultS3Key;
            analysis.ResultS3Key = result?.ResultS3Key;
            analysis.ReportS3Key = result?.ReportS3Key ?? result?.ResultS3Key;
            analysis.PlanS3Key = result?.Summary?.PlanS3Key;
            analysis.TraceS3Key = result?.Summary?.TraceS3Key;
            analysis.CompletedAt = DateTime.UtcNow;
            await db.SaveChangesAsync();

            await audit.LogAsync("analysis_generated", userId, "Analysis", analysisId.ToString(), "success");
            await NotifyAsync(userId, analysisId, "Completed", null);
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
        analysis.Step = null;
        analysis.CompletedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
        await audit.LogAsync("analysis_failed", userId, "Analysis", analysis.Id.ToString(), "failure",
            $"{{\"reason\":\"{EscapeJson(reason)}\"}}");
        await NotifyAsync(userId, analysis.Id, "Failed", null);
    }

    private async Task NotifyAsync(Guid userId, Guid analysisId, string status, string? step)
    {
        await hub.Clients.Group($"user-{userId}")
            .SendAsync("AnalysisUpdate", new { analysisId, status, step });
        await broadcaster.BroadcastAsync(analysisId, userId, status, step);
    }

    private static string EscapeJson(string v) =>
        v.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");

    private static string[] BuildAllowedContexts(string groupContext)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "Regulatory",
        };

        if (!string.IsNullOrWhiteSpace(groupContext))
        {
            foreach (var entry in groupContext.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                set.Add(entry);
        }

        return set.ToArray();
    }
}

internal record AiAnalyzeRequest(
    [property: JsonPropertyName("document_s3_key")] string DocumentS3Key,
    [property: JsonPropertyName("documents_bucket")] string DocumentsBucket,
    [property: JsonPropertyName("document_format")] string DocumentFormat,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("outputs_bucket")] string OutputsBucket,
    [property: JsonPropertyName("output_s3_prefix")] string OutputS3Prefix,
    [property: JsonPropertyName("user_context")] AiUserContext UserContext,
    [property: JsonPropertyName("analysis_id")] Guid AnalysisId,
    [property: JsonPropertyName("callback_url")] string CallbackUrl,
    [property: JsonPropertyName("agentic")] AiAgenticOptions? Agentic);

internal record AiUserContext(
    [property: JsonPropertyName("user_id")] string UserId,
    [property: JsonPropertyName("groups")] string[] Groups);

internal record AiAgenticOptions(
    [property: JsonPropertyName("goal")] string? Goal,
    [property: JsonPropertyName("allowed_contexts")] string[] AllowedContexts,
    [property: JsonPropertyName("requested_output")] string RequestedOutput);

internal record AiAnalyzeResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("result_s3_key")] string? ResultS3Key,
    [property: JsonPropertyName("report_s3_key")] string? ReportS3Key,
    [property: JsonPropertyName("summary")] AiAgenticSummary? Summary,
    [property: JsonPropertyName("warnings")] List<string> Warnings);

internal record AiAgenticSummary(
    [property: JsonPropertyName("plan_s3_key")] string? PlanS3Key,
    [property: JsonPropertyName("trace_s3_key")] string? TraceS3Key);
