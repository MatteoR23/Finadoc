using FinLens.Web.Data;
using FinLens.Web.Services;
using Microsoft.EntityFrameworkCore;

namespace FinLens.Web.Auth;

/// <summary>
/// Authentication against the local SQLite database using PBKDF2-SHA512.
/// </summary>
public class LocalAuthProvider(AppDbContext db, AuditService audit) : IAuthProvider
{
    public async Task<AuthResult> AuthenticateAsync(string username, string password)
    {
        var user = await db.Users
            .AsNoTracking()
            .FirstOrDefaultAsync(u => u.Username == username && u.IsActive);

        if (user is null || !PasswordHasher.VerifyPassword(password, user.PasswordHash))
        {
            await audit.LogAsync(
                action: "login",
                outcome: "failure",
                details: $"{{\"username\":\"{username}\"}}");
            return new AuthResult(false, "Invalid username or password.");
        }

        await audit.LogAsync(action: "login", userId: user.Id, outcome: "success");
        return new AuthResult(true);
    }

    public async Task<UserInfo?> GetUserInfoAsync(string username)
    {
        var user = await db.Users
            .AsNoTracking()
            .Include(u => u.UserGroups)
                .ThenInclude(ug => ug.Group)
            .FirstOrDefaultAsync(u => u.Username == username && u.IsActive);

        if (user is null) return null;

        var groups = user.UserGroups.Select(ug => ug.Group.Name).ToList();
        return new UserInfo(user.Id.ToString(), user.Username, user.IsAdmin, groups);
    }
}
