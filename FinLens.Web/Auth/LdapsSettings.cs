namespace FinLens.Web.Auth;

/// <summary>
/// Configuration model for the LDAPs provider.
/// Bound from the LdapsSettings section in appsettings.json.
/// </summary>
public record LdapsSettings
{
    public string Host { get; init; } = string.Empty;
    public int Port { get; init; } = 636;
    public string BaseDn { get; init; } = string.Empty;
    public string BindDn { get; init; } = string.Empty;
    public string TlsCertPath { get; init; } = string.Empty;
}
