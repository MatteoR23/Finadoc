namespace Finadoc.Web.Services.Storage;

public interface IStorageService
{
    Task UploadAsync(string bucket, string key, Stream content, string contentType, CancellationToken ct = default);
    Task<Stream> DownloadAsync(string bucket, string key, CancellationToken ct = default);
    Task DeleteAsync(string bucket, string key, CancellationToken ct = default);
    Task DeletePrefixAsync(string bucket, string prefix, CancellationToken ct = default);
    Task<string> GeneratePresignedUrlAsync(string bucket, string key, TimeSpan expiry, CancellationToken ct = default);
}
