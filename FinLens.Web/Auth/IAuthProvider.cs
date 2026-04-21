namespace FinLens.Web.Auth;

public record AuthResult(bool Succeeded, string? Error = null);

public record UserInfo(string UserId, string Username, bool IsAdmin, IReadOnlyList<string> Groups);

/// <summary>
/// Abstraction over the authentication backend (local DB or LDAPs directory).
/// The active implementation is selected via Auth:Provider in appsettings.json.
/// </summary>
public interface IAuthProvider
{
    Task<AuthResult> AuthenticateAsync(string username, string password);
    Task<UserInfo?> GetUserInfoAsync(string username);
}
