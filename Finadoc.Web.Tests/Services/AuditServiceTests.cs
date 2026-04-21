using Finadoc.Web.Data;
using Finadoc.Web.Services;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Tests.Services;

public class AuditServiceTests
{
    private static AppDbContext CreateDb() =>
        new(new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options);

    [Fact]
    public async Task LogAsync_SavesAuditEventWithAllFields()
    {
        var db = CreateDb();
        var service = new AuditService(db);

        await service.LogAsync(
            action: "test_action",
            userId: Guid.Parse("00000000-0000-0000-0000-000000000001"),
            targetType: "TargetType",
            targetId: "target-id",
            outcome: "failure",
            details: "{\"reason\":\"unit_test\"}");

        var evt = db.AuditEvents.Single();
        Assert.Equal("test_action", evt.Action);
        Assert.Equal(Guid.Parse("00000000-0000-0000-0000-000000000001"), evt.UserId);
        Assert.Equal("TargetType", evt.TargetType);
        Assert.Equal("target-id", evt.TargetId);
        Assert.Equal("failure", evt.Outcome);
        Assert.Equal("{\"reason\":\"unit_test\"}", evt.Details);
    }
}
