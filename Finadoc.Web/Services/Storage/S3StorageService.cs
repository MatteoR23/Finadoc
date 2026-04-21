using Amazon.S3;
using Amazon.S3.Model;

namespace Finadoc.Web.Services.Storage;

public class S3StorageService(IAmazonS3 s3, ILogger<S3StorageService> logger) : IStorageService
{
    public async Task UploadAsync(string bucket, string key, Stream content, string contentType, CancellationToken ct = default)
    {
        var request = new PutObjectRequest
        {
            BucketName = bucket,
            Key = key,
            InputStream = content,
            ContentType = contentType,
            UseChunkEncoding = false,
        };
        await s3.PutObjectAsync(request, ct);
        logger.LogDebug("Uploaded s3://{Bucket}/{Key}", bucket, key);
    }

    public async Task<Stream> DownloadAsync(string bucket, string key, CancellationToken ct = default)
    {
        var response = await s3.GetObjectAsync(bucket, key, ct);
        return response.ResponseStream;
    }

    public async Task DeleteAsync(string bucket, string key, CancellationToken ct = default)
    {
        await s3.DeleteObjectAsync(bucket, key, ct);
        logger.LogDebug("Deleted s3://{Bucket}/{Key}", bucket, key);
    }

    public async Task DeletePrefixAsync(string bucket, string prefix, CancellationToken ct = default)
    {
        var list = await s3.ListObjectsV2Async(new ListObjectsV2Request
        {
            BucketName = bucket,
            Prefix = prefix,
        }, ct);

        if (list.S3Objects.Count == 0) return;

        var deleteRequest = new DeleteObjectsRequest
        {
            BucketName = bucket,
            Objects = list.S3Objects.Select(o => new KeyVersion { Key = o.Key }).ToList(),
        };
        await s3.DeleteObjectsAsync(deleteRequest, ct);
        logger.LogDebug("Deleted {Count} objects with prefix s3://{Bucket}/{Prefix}", list.S3Objects.Count, bucket, prefix);
    }
}
