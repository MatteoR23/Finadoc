using FinLens.Web.Auth;
using FinLens.Web.Data;
using FinLens.Web.Models;
using FinLens.Web.Services;
using Microsoft.EntityFrameworkCore;

namespace FinLens.Web.Tests.Services;

public class UserServiceTests
{
    private static AppDbContext CreateDb() =>
        new(new DbContextOptionsBuilder<AppDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options);

    private static (UserService service, AppDbContext db) CreateService()
    {
        var db = CreateDb();
        var audit = new AuditService(db);
        return (new UserService(db, audit), db);
    }

    // ── CreateAdminAsync ─────────────────────────────────────────────────────

    [Fact]
    public async Task CreateAdminAsync_CreatesUserWithIsAdminTrue()
    {
        var (service, db) = CreateService();

        await service.CreateAdminAsync("admin", "password");

        var user = db.Users.Single();
        Assert.Equal("admin", user.Username);
        Assert.True(user.IsAdmin);
        Assert.True(user.IsActive);
        Assert.Empty(await db.UserGroups.ToListAsync());
    }

    [Fact]
    public async Task CreateAdminAsync_StoresHashedPassword()
    {
        var (service, db) = CreateService();

        await service.CreateAdminAsync("admin", "plaintext");

        var user = db.Users.Single();
        // Must not store plaintext
        Assert.NotEqual("plaintext", user.PasswordHash);
        // Must be verifiable
        Assert.True(PasswordHasher.VerifyPassword("plaintext", user.PasswordHash));
    }

    [Fact]
    public async Task CreateAdminAsync_LogsUserCreatedAuditEvent()
    {
        var (service, db) = CreateService();

        await service.CreateAdminAsync("admin", "password");

        var evt = db.AuditEvents.Single();
        Assert.Equal("user_created", evt.Action);
        Assert.Equal("success", evt.Outcome);
    }

    // ── CreateUserAsync ──────────────────────────────────────────────────────

    [Fact]
    public async Task CreateUserAsync_CreatesUserGroupRows_ForEachGroupId()
    {
        var (service, db) = CreateService();

        await service.CreateUserAsync("pm_user", "pass", isAdmin: false, groupIds: [1, 2]);

        var user = db.Users.Single();
        Assert.Equal("pm_user", user.Username);
        Assert.False(user.IsAdmin);

        var groups = await db.UserGroups.Where(ug => ug.UserId == user.Id).ToListAsync();
        Assert.Equal(2, groups.Count);
        Assert.Contains(groups, ug => ug.GroupId == 1);
        Assert.Contains(groups, ug => ug.GroupId == 2);
    }

    [Fact]
    public async Task CreateUserAsync_WithNoGroups_CreatesNoUserGroupRows()
    {
        var (service, db) = CreateService();

        await service.CreateUserAsync("standalone", "pass", isAdmin: false, groupIds: []);

        Assert.Single(db.Users);
        Assert.Empty(db.UserGroups);
    }

    [Fact]
    public async Task CreateUserAsync_LogsGroupAssignedAuditEvent_WhenGroupIdsAreProvided()
    {
        var (service, db) = CreateService();

        await service.CreateUserAsync("pm_user", "pass", isAdmin: false, groupIds: [1, 2], createdByUserId: Guid.NewGuid());

        Assert.Equal(2, db.AuditEvents.Count());
        Assert.Contains(db.AuditEvents, e => e.Action == "group_assigned");
    }

    [Fact]
    public async Task GetAllUsersAsync_ReturnsUsersOrderedByUsernameWithGroups()
    {
        var (service, db) = CreateService();
        var userA = new User { Username = "alice", PasswordHash = PasswordHasher.HashPassword("x") };
        var userB = new User { Username = "bob", PasswordHash = PasswordHasher.HashPassword("x") };
        db.Users.AddRange(userB, userA);
        db.Groups.Add(new Group { Id = 1, Name = "PM" });
        await db.SaveChangesAsync();
        db.UserGroups.Add(new UserGroup { UserId = userA.Id, GroupId = 1 });
        await db.SaveChangesAsync();

        var users = await service.GetAllUsersAsync();

        Assert.Equal(2, users.Count);
        Assert.Equal("alice", users[0].Username);
        Assert.Equal("bob", users[1].Username);
        Assert.Single(users[0].UserGroups);
    }

    [Fact]
    public async Task GetUserAsync_ReturnsUserWithGroups_WhenExists()
    {
        var (service, db) = CreateService();
        var user = new User { Username = "carol", PasswordHash = PasswordHasher.HashPassword("x") };
        db.Users.Add(user);
        db.Groups.Add(new Group { Id = 1, Name = "RM" });
        await db.SaveChangesAsync();
        db.UserGroups.Add(new UserGroup { UserId = user.Id, GroupId = 1 });
        await db.SaveChangesAsync();

        var result = await service.GetUserAsync(user.Id);

        Assert.NotNull(result);
        Assert.Equal("carol", result!.Username);
        Assert.Single(result.UserGroups);
        Assert.Equal(1, result.UserGroups.Single().GroupId);
    }

    [Fact]
    public async Task GetUserAsync_ReturnsNull_WhenNotFound()
    {
        var (service, _) = CreateService();

        var result = await service.GetUserAsync(Guid.NewGuid());

        Assert.Null(result);
    }

    [Fact]
    public async Task UpdateUserAsync_UpdatesUserAndLogsAuditEvent()
    {
        var (service, db) = CreateService();
        var user = new User { Username = "user", PasswordHash = PasswordHasher.HashPassword("x") };
        db.Users.Add(user);
        db.UserGroups.Add(new UserGroup { UserId = user.Id, GroupId = 1 });
        await db.SaveChangesAsync();

        await service.UpdateUserAsync(user.Id, "updated", true, [2], actingUserId: Guid.NewGuid());

        var updated = db.Users.Single();
        Assert.Equal("updated", updated.Username);
        Assert.True(updated.IsAdmin);
        Assert.Single(db.UserGroups);
        Assert.Equal(2, db.UserGroups.Single().GroupId);
        Assert.Contains(db.AuditEvents, e => e.Action == "user_updated");
    }

    [Fact]
    public async Task ResetPasswordAsync_UpdatesHashAndLogsAuditEvent()
    {
        var (service, db) = CreateService();
        var user = new User { Username = "user", PasswordHash = PasswordHasher.HashPassword("old") };
        db.Users.Add(user);
        await db.SaveChangesAsync();

        await service.ResetPasswordAsync(user.Id, "new", actingUserId: Guid.NewGuid());

        var updated = db.Users.Single();
        Assert.True(PasswordHasher.VerifyPassword("new", updated.PasswordHash));
        Assert.Contains(db.AuditEvents, e => e.Action == "password_reset");
    }

    [Fact]
    public async Task DeactivateUserAsync_DoesNothing_WhenUserNotFound()
    {
        var (service, db) = CreateService();

        await service.DeactivateUserAsync(Guid.NewGuid());

        Assert.Empty(await db.Users.ToListAsync());
    }

    [Fact]
    public async Task ReactivateUserAsync_DoesNothing_WhenUserNotFound()
    {
        var (service, db) = CreateService();

        await service.ReactivateUserAsync(Guid.NewGuid());

        Assert.Empty(await db.Users.ToListAsync());
    }

    [Fact]
    public async Task AssignGroupsAsync_RemovesAllMemberships_WhenNoGroupsProvided()
    {
        var (service, db) = CreateService();
        var user = new User { Username = "user", PasswordHash = PasswordHasher.HashPassword("x") };
        db.Users.Add(user);
        db.UserGroups.Add(new UserGroup { UserId = user.Id, GroupId = 1 });
        await db.SaveChangesAsync();

        await service.AssignGroupsAsync(user.Id, []);

        Assert.Empty(db.UserGroups);
        Assert.Contains(db.AuditEvents, e => e.Action == "group_assigned");
    }

    // ── DeleteUserAsync ──────────────────────────────────────────────────────

    [Fact]
    public async Task DeleteUserAsync_ThrowsInvalidOperation_WhenDeletingOwnAccount()
    {
        var (service, db) = CreateService();
        var userId = Guid.NewGuid();
        db.Users.Add(new User
        {
            Id = userId,
            Username = "self",
            PasswordHash = PasswordHasher.HashPassword("x"),
        });
        await db.SaveChangesAsync();

        await Assert.ThrowsAsync<InvalidOperationException>(
            () => service.DeleteUserAsync(userId, actingUserId: userId));
    }

    [Fact]
    public async Task DeleteUserAsync_RemovesUser_WhenActingUserIsDifferent()
    {
        var (service, db) = CreateService();
        var targetId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        db.Users.Add(new User
        {
            Id = targetId,
            Username = "target",
            PasswordHash = PasswordHasher.HashPassword("x"),
        });
        await db.SaveChangesAsync();

        await service.DeleteUserAsync(targetId, actingUserId: actorId);

        Assert.Empty(db.Users);
        var evt = db.AuditEvents.Single();
        Assert.Equal("user_deleted", evt.Action);
        Assert.Equal(actorId, evt.UserId);
    }

    [Fact]
    public async Task DeleteUserAsync_IsIdempotent_WhenUserDoesNotExist()
    {
        var (service, _) = CreateService();

        // Should not throw even when user is missing
        await service.DeleteUserAsync(Guid.NewGuid(), actingUserId: Guid.NewGuid());
    }

    // ── UpdatePasswordAsync ──────────────────────────────────────────────────

    [Fact]
    public async Task UpdatePasswordAsync_UpdatesHashAndLogsAuditEvent()
    {
        var (service, db) = CreateService();
        var user = new User
        {
            Username = "user",
            PasswordHash = PasswordHasher.HashPassword("old"),
        };
        db.Users.Add(user);
        await db.SaveChangesAsync();

        await service.UpdatePasswordAsync(user.Id, "new");

        var updated = db.Users.Single();
        Assert.True(PasswordHasher.VerifyPassword("new", updated.PasswordHash));
        Assert.False(PasswordHasher.VerifyPassword("old", updated.PasswordHash));

        var evt = db.AuditEvents.Single();
        Assert.Equal("password_changed", evt.Action);
        Assert.Equal(user.Id, evt.UserId);
    }

    // ── DeactivateUserAsync / ReactivateUserAsync ────────────────────────────

    [Fact]
    public async Task DeactivateUserAsync_SetsIsActiveFalse()
    {
        var (service, db) = CreateService();
        var user = new User
        {
            Username = "user",
            PasswordHash = PasswordHasher.HashPassword("x"),
            IsActive = true,
        };
        db.Users.Add(user);
        await db.SaveChangesAsync();

        await service.DeactivateUserAsync(user.Id);

        Assert.False(db.Users.Single().IsActive);
    }

    [Fact]
    public async Task ReactivateUserAsync_SetsIsActiveTrue()
    {
        var (service, db) = CreateService();
        var user = new User
        {
            Username = "user",
            PasswordHash = PasswordHasher.HashPassword("x"),
            IsActive = false,
        };
        db.Users.Add(user);
        await db.SaveChangesAsync();

        await service.ReactivateUserAsync(user.Id);

        Assert.True(db.Users.Single().IsActive);
    }

    // ── AssignGroupsAsync ────────────────────────────────────────────────────

    [Fact]
    public async Task AssignGroupsAsync_ReplacesExistingMemberships()
    {
        var (service, db) = CreateService();
        var user = new User
        {
            Username = "user",
            PasswordHash = PasswordHasher.HashPassword("x"),
        };
        db.Users.Add(user);
        db.UserGroups.Add(new UserGroup { UserId = user.Id, GroupId = 1 });
        await db.SaveChangesAsync();

        // Replace group 1 with group 2
        await service.AssignGroupsAsync(user.Id, [2]);

        var memberships = await db.UserGroups.Where(ug => ug.UserId == user.Id).ToListAsync();
        Assert.Single(memberships);
        Assert.Equal(2, memberships[0].GroupId);
    }
}
