using System.Linq.Expressions;
using Finadoc.Web.Data;
using Finadoc.Web.Jobs;
using Finadoc.Web.Models;
using Finadoc.Web.Services;
using Hangfire;
using Hangfire.Common;
using Hangfire.States;
using Microsoft.EntityFrameworkCore;
using Moq;

namespace Finadoc.Web.Tests.Services;

public class AnalysisServiceTests
{
    private static AppDbContext CreateDb() =>
        new(new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options);

    [Fact]
    public async Task StartAnalysisAsync_CreatesQueuedAnalysis_AndEnqueuesJob()
    {
        var db = CreateDb();
        var document = new Document
        {
            Id = Guid.NewGuid(),
            UserId = Guid.NewGuid(),
            OriginalFileName = "report.pdf",
            Format = "pdf",
            UploadedAt = DateTime.UtcNow,
            ExpiresAt = DateTime.UtcNow.AddDays(90),
        };
        db.Documents.Add(document);
        await db.SaveChangesAsync();

        var jobs = new Mock<IBackgroundJobClient>(MockBehavior.Strict);
        jobs.Setup(j => j.Create(It.IsAny<Job>(), It.IsAny<IState>()))
            .Returns("job-id");

        var service = new AnalysisService(db, jobs.Object);

        var analysis = await service.StartAnalysisAsync(document.Id, "PM", Guid.NewGuid());

        Assert.Equal(document.Id, analysis.DocumentId);
        Assert.Equal("PM", analysis.GroupContext);
        Assert.Equal("Queued", analysis.Status);
        Assert.True(analysis.ExpiresAt > DateTime.UtcNow.AddDays(89));
        Assert.True(analysis.ExpiresAt < DateTime.UtcNow.AddDays(91));

        jobs.Verify(j => j.Create(It.IsAny<Job>(), It.IsAny<IState>()), Times.Once);
    }

    [Fact]
    public async Task GetLatestByDocumentIdsAsync_ReturnsLatestAnalysisForEachDocument()
    {
        var db = CreateDb();
        var documentA = Guid.NewGuid();
        var documentB = Guid.NewGuid();

        db.Analyses.AddRange(
            new Analysis
            {
                DocumentId = documentA,
                GroupContext = "PM",
                Status = "Completed",
                StartedAt = DateTime.UtcNow.AddHours(-2),
                ExpiresAt = DateTime.UtcNow.AddDays(90),
            },
            new Analysis
            {
                DocumentId = documentA,
                GroupContext = "PM",
                Status = "Failed",
                StartedAt = DateTime.UtcNow.AddHours(-1),
                ExpiresAt = DateTime.UtcNow.AddDays(90),
            },
            new Analysis
            {
                DocumentId = documentB,
                GroupContext = "RM",
                Status = "Queued",
                StartedAt = DateTime.UtcNow.AddHours(-3),
                ExpiresAt = DateTime.UtcNow.AddDays(90),
            });
        await db.SaveChangesAsync();

        var service = new AnalysisService(db, Mock.Of<IBackgroundJobClient>());

        var latest = await service.GetLatestByDocumentIdsAsync(new[] { documentA, documentB });

        Assert.Equal(2, latest.Count);
        Assert.Equal("Failed", latest[documentA]?.Status);
        Assert.Equal("Queued", latest[documentB]?.Status);
    }
}
