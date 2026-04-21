namespace FinLens.Web.Services;

public class AnalysisProgressBroadcaster
{
    public event Func<AnalysisProgressEvent, Task>? OnUpdate;

    internal async Task BroadcastAsync(Guid analysisId, Guid userId, string status, string? step)
    {
        var handler = OnUpdate;
        if (handler is null) return;
        foreach (var d in handler.GetInvocationList().Cast<Func<AnalysisProgressEvent, Task>>())
        {
            try { await d(new AnalysisProgressEvent(analysisId, userId, status, step)); }
            catch { /* isolate bad subscribers */ }
        }
    }
}

public record AnalysisProgressEvent(Guid AnalysisId, Guid UserId, string Status, string? Step);
