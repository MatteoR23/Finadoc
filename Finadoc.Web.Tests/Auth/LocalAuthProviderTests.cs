using Finadoc.Web.Auth;
using Finadoc.Web.Data;
using Finadoc.Web.Models;
using Finadoc.Web.Services;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Tests.Auth;

public class LocalAuthProviderTests
{
    // Each test gets an isolated in-memory database by using a unique name.
    private static AppDbContext CreateDb() =>
        new(new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options);

    private static (LocalAuthProvider provider, AppDbContext db) CreateProvider()
    {
        var db = CreateDb();
        var audit = new AuditService(db);
        return (new LocalAuthProvider(db, audit), db);
    }

    // ── AuthenticateAsync ────────────────────────────────────────────────────

    [Fact]
    public async Task AuthenticateAsync_ReturnsFalse_WhenUserDoesNotExist()
    {
        var (provider, db) = CreateProvider();

        var result = await provider.AuthenticateAsync("nobody", "pass");

        Assert.False(result.Succeeded);
        Assert.NotNull(result.Error);
        // A failure audit event must have been written
        var evt = db.AuditEvents.Single();
        Assert.Equal("login", evt.Action);
        Assert.Equal("failure", evt.Outcome);
    }

    [Fact]
    public async Task AuthenticateAsync_ReturnsFalse_WhenUserIsInactive()
    {
        var (provider, db) = CreateProvider();
        db.Users.Add(new User
        {
            Username = "inactive",
            PasswordHash = PasswordHasher.HashPassword("pass"),
            IsActive = false,
        });
        await db.SaveChangesAsync();

        var result = await provider.AuthenticateAsync("inactive", "pass");

        Assert.False(result.Succeeded);
    }

    [Fact]
    public async Task AuthenticateAsync_ReturnsFalse_WhenPasswordIsWrong()
    {
        var (provider, db) = CreateProvider();
        db.Users.Add(new User
        {
            Username = "user",
            PasswordHash = PasswordHasher.HashPassword("correct"),
            IsActive = true,
        });
        await db.SaveChangesAsync();

        var result = await provider.AuthenticateAsync("user", "wrong");

        Assert.False(result.Succeeded);
        var evt = db.AuditEvents.Single();
        Assert.Equal("login", evt.Action);
        Assert.Equal("failure", evt.Outcome);
    }

    [Fact]
    public async Task AuthenticateAsync_ReturnsTrue_AndLogsSuccess_WhenCredentialsAreValid()
    {
        var (provider, db) = CreateProvider();
        var user = new User
        {
            Username = "admin",
            PasswordHash = PasswordHasher.HashPassword("secret"),
            IsActive = true,
        };
        db.Users.Add(user);
        await db.SaveChangesAsync();

        var result = await provider.AuthenticateAsync("admin", "secret");

        Assert.True(result.Succeeded);
        Assert.Null(result.Error);
        var evt = db.AuditEvents.Single();
        Assert.Equal("login", evt.Action);
        Assert.Equal("success", evt.Outcome);
        Assert.Equal(user.Id, evt.UserId);
    }

    // ── GetUserInfoAsync ─────────────────────────────────────────────────────

    [Fact]
    public async Task GetUserInfoAsync_ReturnsNull_WhenUserDoesNotExist()
    {
        var (provider, _) = CreateProvider();

        var info = await provider.GetUserInfoAsync("nobody");

        Assert.Null(info);
    }

    [Fact]
    public async Task GetUserInfoAsync_ReturnsNull_WhenUserIsInactive()
    {
        var (provider, db) = CreateProvider();
        db.Users.Add(new User
        {
            Username = "inactive",
            PasswordHash = PasswordHasher.HashPassword("x"),
            IsActive = false,
        });
        await db.SaveChangesAsync();

        var info = await provider.GetUserInfoAsync("inactive");

        Assert.Null(info);
    }

    [Fact]
    public async Task GetUserInfoAsync_ReturnsCorrectUserInfo_WithGroups()
    {
        var (provider, db) = CreateProvider();
        var user = new User
        {
            Username = "pm_user",
            PasswordHash = PasswordHasher.HashPassword("x"),
            IsAdmin = false,
            IsActive = true,
        };
        db.Users.Add(user);
        db.Groups.Add(new Group { Id = 99, Name = "PM" });
        await db.SaveChangesAsync();
        db.UserGroups.Add(new UserGroup { UserId = user.Id, GroupId = 99 });
        await db.SaveChangesAsync();

        var info = await provider.GetUserInfoAsync("pm_user");

        Assert.NotNull(info);
        Assert.Equal("pm_user", info.Username);
        Assert.Equal(user.Id.ToString(), info.UserId);
        Assert.False(info.IsAdmin);
        Assert.Single(info.Groups);
        Assert.Contains("PM", info.Groups);
    }

    [Fact]
    public async Task GetUserInfoAsync_ReturnsIsAdmin_True_WhenUserIsAdmin()
    {
        var (provider, db) = CreateProvider();
        db.Users.Add(new User
        {
            Username = "admin",
            PasswordHash = PasswordHasher.HashPassword("x"),
            IsAdmin = true,
            IsActive = true,
        });
        await db.SaveChangesAsync();

        var info = await provider.GetUserInfoAsync("admin");

        Assert.NotNull(info);
        Assert.True(info.IsAdmin);
        Assert.Empty(info.Groups);
    }
}
