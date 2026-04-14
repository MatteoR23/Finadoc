using Finadoc.Web.Auth;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Security.Claims;

namespace Finadoc.Web.Pages;

[AllowAnonymous]
[ValidateAntiForgeryToken]
public class LoginModel(IAuthProvider authProvider) : PageModel
{
    public string? ErrorMessage { get; private set; }
    public string Username { get; private set; } = string.Empty;

    public IActionResult OnGet()
    {
        // Already authenticated — go to home
        if (User.Identity?.IsAuthenticated == true)
            return Redirect("/");
        return Page();
    }

    public async Task<IActionResult> OnPostAsync(string username, string password, string? returnUrl = null)
    {
        Username = username ?? string.Empty;

        var result = await authProvider.AuthenticateAsync(username ?? string.Empty, password ?? string.Empty);
        if (!result.Succeeded)
        {
            ErrorMessage = result.Error ?? "Invalid username or password.";
            return Page();
        }

        var userInfo = await authProvider.GetUserInfoAsync(username!);
        if (userInfo is null)
        {
            ErrorMessage = "Unable to load user information.";
            return Page();
        }

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, userInfo.UserId),
            new(ClaimTypes.Name, userInfo.Username),
            new("IsAdmin", userInfo.IsAdmin ? "true" : "false"),
        };

        foreach (var group in userInfo.Groups)
            claims.Add(new Claim(ClaimTypes.Role, group));

        var identity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
        var principal = new ClaimsPrincipal(identity);

        var props = new AuthenticationProperties
        {
            IsPersistent = true,
            ExpiresUtc = DateTimeOffset.UtcNow.AddHours(8),
            AllowRefresh = true,
        };

        await HttpContext.SignInAsync(CookieAuthenticationDefaults.AuthenticationScheme, principal, props);

        // Redirect to returnUrl only if it is a local URL (prevent open redirect)
        if (!string.IsNullOrEmpty(returnUrl) && Url.IsLocalUrl(returnUrl))
            return Redirect(returnUrl);

        return Redirect("/");
    }
}
