using Microsoft.AspNetCore.Components.Authorization;
using System.Security.Claims;

namespace Finadoc.Web.Auth;

/// <summary>
/// Bridges ASP.NET Core cookie authentication (HTTP layer) into Blazor Server's
/// cascading authentication state (SignalR layer).
///
/// How it works: The cookie is validated once during the initial HTTP request that
/// upgrades to a WebSocket. After the upgrade, there is no HttpContext. This provider
/// captures the ClaimsPrincipal from the HttpContext during the first call (prerender
/// or circuit initialization) and caches it for the lifetime of the circuit.
/// </summary>
public class CookieAuthStateProvider(IHttpContextAccessor httpContextAccessor)
    : AuthenticationStateProvider
{
    private AuthenticationState? _cached;

    public override Task<AuthenticationState> GetAuthenticationStateAsync()
    {
        if (_cached is not null)
            return Task.FromResult(_cached);

        // HttpContext is only available during the initial HTTP request.
        // After the WebSocket upgrade it returns null — the cached value handles that.
        var user = httpContextAccessor.HttpContext?.User
            ?? new ClaimsPrincipal(new ClaimsIdentity());

        _cached = new AuthenticationState(user);
        return Task.FromResult(_cached);
    }

    /// <summary>
    /// Forces Blazor to re-evaluate the auth state and re-render protected components.
    /// Call this after a programmatic state change (e.g. after logout within the circuit).
    /// Note: login/logout normally navigate away via a full HTTP round-trip, so this is
    /// mainly needed for edge cases like session expiry detection.
    /// </summary>
    public void NotifyAuthStateChanged(ClaimsPrincipal user)
    {
        _cached = new AuthenticationState(user);
        NotifyAuthenticationStateChanged(Task.FromResult(_cached));
    }
}
