namespace Finadoc.Web.Auth;

/// <summary>
/// LDAPs authentication stub.
/// All methods throw NotImplementedException — the interface and config model
/// are in place so binding can be added post-POC without breaking changes.
///
/// When implemented: use Novell.Directory.Ldap.NETStandard, port 636, TLS enforced.
/// </summary>
public class LdapsAuthProvider(LdapsSettings settings) : IAuthProvider
{
    public Task<AuthResult> AuthenticateAsync(string username, string password)
    {
        throw new NotImplementedException("LDAPs binding is not implemented in the POC.");
    }

    public Task<UserInfo?> GetUserInfoAsync(string username)
    {
        throw new NotImplementedException("LDAPs binding is not implemented in the POC.");
    }
}
