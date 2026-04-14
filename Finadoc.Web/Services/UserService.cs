using Finadoc.Web.Auth;
using Finadoc.Web.Data;
using Finadoc.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Services;

public class UserService(AppDbContext db, AuditService audit)
{
    /// <summary>Creates the first admin account during first-run setup.</summary>
    public async Task CreateAdminAsync(string username, string password)
    {
        var user = new User
        {
            Username = username,
            PasswordHash = PasswordHasher.HashPassword(password),
            IsAdmin = true,
            IsActive = true,
        };
        db.Users.Add(user);
        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "user_created",
            userId: user.Id,
            targetType: "User",
            targetId: user.Id.ToString(),
            outcome: "success",
            details: "{\"isAdmin\":true,\"source\":\"first_run_setup\"}");
    }

    /// <summary>Creates a new user and assigns them to the specified groups.</summary>
    public async Task CreateUserAsync(
        string username,
        string password,
        bool isAdmin,
        IEnumerable<int> groupIds,
        Guid? createdByUserId = null)
    {
        var user = new User
        {
            Username = username,
            PasswordHash = PasswordHasher.HashPassword(password),
            IsAdmin = isAdmin,
            IsActive = true,
        };
        db.Users.Add(user);

        foreach (var gid in groupIds)
            db.UserGroups.Add(new UserGroup { UserId = user.Id, GroupId = gid });

        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "user_created",
            userId: createdByUserId,
            targetType: "User",
            targetId: user.Id.ToString(),
            outcome: "success");

        if (groupIds.Any())
            await audit.LogAsync(
                action: "group_assigned",
                userId: createdByUserId,
                targetType: "User",
                targetId: user.Id.ToString(),
                outcome: "success");
    }

    /// <summary>Returns all users with their group memberships.</summary>
    public async Task<List<User>> GetAllUsersAsync()
    {
        return await db.Users
            .Include(u => u.UserGroups)
                .ThenInclude(ug => ug.Group)
            .OrderBy(u => u.Username)
            .ToListAsync();
    }

    /// <summary>Deactivates a user (soft delete — they cannot log in but their data is preserved).</summary>
    public async Task DeactivateUserAsync(Guid userId, Guid? actingUserId = null)
    {
        var user = await db.Users.FindAsync(userId);
        if (user is null) return;

        user.IsActive = false;
        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "user_deactivated",
            userId: actingUserId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
    }

    /// <summary>Updates a user's password hash.</summary>
    public async Task UpdatePasswordAsync(Guid userId, string newPassword)
    {
        var user = await db.Users.FindAsync(userId);
        if (user is null) return;

        user.PasswordHash = PasswordHasher.HashPassword(newPassword);
        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "password_changed",
            userId: userId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
    }

    /// <summary>Replaces a user's group memberships.</summary>
    public async Task AssignGroupsAsync(Guid userId, IEnumerable<int> groupIds, Guid? actingUserId = null)
    {
        var existing = await db.UserGroups
            .Where(ug => ug.UserId == userId)
            .ToListAsync();
        db.UserGroups.RemoveRange(existing);

        foreach (var gid in groupIds)
            db.UserGroups.Add(new UserGroup { UserId = userId, GroupId = gid });

        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "group_assigned",
            userId: actingUserId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
    }
}
