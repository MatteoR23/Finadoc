using Finadoc.Web.Data;

namespace Finadoc.Web.Auth;

/// <summary>
/// Authentication against the local SQLite database using PBKDF2-SHA512.
/// Full implementation in P2.
/// </summary>
public class LocalAuthProvider(AppDbContext db) : IAuthProvider
{
    public Task<AuthResult> AuthenticateAsync(string username, string password)
    {
        // TODO (P2): look up user in DB, verify PBKDF2-SHA512 hash
        throw new NotImplementedException("Local auth not implemented yet (P2)");
    }

    public Task<UserInfo?> GetUserInfoAsync(string username)
    {
        // TODO (P2): load user + groups from DB
        throw new NotImplementedException("Local auth not implemented yet (P2)");
    }
}
