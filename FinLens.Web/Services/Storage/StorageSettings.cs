namespace FinLens.Web.Services.Storage;

public class StorageSettings
{
    public string Provider { get; set; } = "minio";
    public string? Endpoint { get; set; }
    public string? PublicEndpoint { get; set; }
    public string Region { get; set; } = "eu-south-1";
    public string AccessKey { get; set; } = "";
    public string SecretKey { get; set; } = "";
    public string DocumentsBucket { get; set; } = "finlens-documents";
    public string OutputsBucket { get; set; } = "finlens-outputs";
}
