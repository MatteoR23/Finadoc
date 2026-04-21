using FinLens.Web.Auth;
using FinLens.Web.Data;
using FinLens.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace FinLens.Web.Services;

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

    /// <summary>Returns a single user with group memberships, or null.</summary>
    public async Task<User?> GetUserAsync(Guid userId)
    {
        return await db.Users
            .Include(u => u.UserGroups)
                .ThenInclude(ug => ug.Group)
            .FirstOrDefaultAsync(u => u.Id == userId);
    }

    /// <summary>Updates username, admin flag, and group memberships.</summary>
    public async Task UpdateUserAsync(
        Guid userId,
        string username,
        bool isAdmin,
        IEnumerable<int> groupIds,
        Guid? actingUserId = null)
    {
        var user = await db.Users.FindAsync(userId)
            ?? throw new InvalidOperationException("User not found.");

        user.Username = username;
        user.IsAdmin = isAdmin;

        // Replace group memberships
        var existing = await db.UserGroups.Where(ug => ug.UserId == userId).ToListAsync();
        db.UserGroups.RemoveRange(existing);
        foreach (var gid in groupIds)
            db.UserGroups.Add(new UserGroup { UserId = userId, GroupId = gid });

        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "user_updated",
            userId: actingUserId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
    }

    /// <summary>Resets a user's password (admin action — no current-password check).</summary>
    public async Task ResetPasswordAsync(Guid userId, string newPassword, Guid? actingUserId = null)
    {
        var user = await db.Users.FindAsync(userId);
        if (user is null) return;

        user.PasswordHash = PasswordHasher.HashPassword(newPassword);
        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "password_reset",
            userId: actingUserId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
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

    /// <summary>Reactivates a previously deactivated user.</summary>
    public async Task ReactivateUserAsync(Guid userId, Guid? actingUserId = null)
    {
        var user = await db.Users.FindAsync(userId);
        if (user is null) return;

        user.IsActive = true;
        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "user_reactivated",
            userId: actingUserId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
    }

    /// <summary>
    /// Permanently deletes a user and all their data (documents, analyses cascade via FK).
    /// Cannot delete yourself.
    /// </summary>
    public async Task DeleteUserAsync(Guid userId, Guid? actingUserId = null)
    {
        if (userId == actingUserId)
            throw new InvalidOperationException("Cannot delete your own account.");

        var user = await db.Users.FindAsync(userId);
        if (user is null) return;

        db.Users.Remove(user);
        await db.SaveChangesAsync();

        await audit.LogAsync(
            action: "user_deleted",
            userId: actingUserId,
            targetType: "User",
            targetId: userId.ToString(),
            outcome: "success");
    }

    /// <summary>Updates a user's password hash (self-service — caller must verify current password first).</summary>
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
