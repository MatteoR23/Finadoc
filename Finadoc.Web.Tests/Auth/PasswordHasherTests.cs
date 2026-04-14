using Finadoc.Web.Auth;

namespace Finadoc.Web.Tests.Auth;

public class PasswordHasherTests
{
    [Fact]
    public void HashPassword_ReturnsColonSeparatedBase64()
    {
        var hash = PasswordHasher.HashPassword("anypassword");

        var parts = hash.Split(':');
        Assert.Equal(2, parts.Length);
        Assert.True(IsBase64(parts[0]), "Salt is not valid base64");
        Assert.True(IsBase64(parts[1]), "Hash is not valid base64");
    }

    [Fact]
    public void HashPassword_ProducesDifferentHashesForSamePassword()
    {
        // Each call generates a new random salt — output must be unique
        var h1 = PasswordHasher.HashPassword("same");
        var h2 = PasswordHasher.HashPassword("same");

        Assert.NotEqual(h1, h2);
    }

    [Fact]
    public void VerifyPassword_ReturnsTrueForCorrectPassword()
    {
        var hash = PasswordHasher.HashPassword("correct");

        Assert.True(PasswordHasher.VerifyPassword("correct", hash));
    }

    [Fact]
    public void VerifyPassword_ReturnsFalseForWrongPassword()
    {
        var hash = PasswordHasher.HashPassword("correct");

        Assert.False(PasswordHasher.VerifyPassword("wrong", hash));
    }

    [Fact]
    public void VerifyPassword_ReturnsFalseForEmptyPassword()
    {
        var hash = PasswordHasher.HashPassword("correct");

        Assert.False(PasswordHasher.VerifyPassword("", hash));
    }

    [Fact]
    public void VerifyPassword_ReturnsFalseForTamperedHashPart()
    {
        var hash = PasswordHasher.HashPassword("password");
        var salt = hash.Split(':')[0];
        var tampered = salt + ":" + Convert.ToBase64String(new byte[64]); // all-zero hash

        Assert.False(PasswordHasher.VerifyPassword("password", tampered));
    }

    [Fact]
    public void VerifyPassword_ReturnsFalseForMalformedStoredHash()
    {
        Assert.False(PasswordHasher.VerifyPassword("password", "no-colon-here"));
        Assert.False(PasswordHasher.VerifyPassword("password", ""));
        Assert.False(PasswordHasher.VerifyPassword("password", "::"));
        Assert.False(PasswordHasher.VerifyPassword("password", "notbase64!:notbase64!"));
    }

    [Fact]
    public void VerifyPassword_IsTrueOnlyForExactMatch()
    {
        var hash = PasswordHasher.HashPassword("Password1!");

        Assert.False(PasswordHasher.VerifyPassword("password1!", hash)); // case difference
        Assert.False(PasswordHasher.VerifyPassword("Password1", hash));  // missing char
        Assert.False(PasswordHasher.VerifyPassword("Password1! ", hash)); // trailing space
        Assert.True(PasswordHasher.VerifyPassword("Password1!", hash));
    }

    private static bool IsBase64(string s)
    {
        if (string.IsNullOrEmpty(s)) return false;
        try { Convert.FromBase64String(s); return true; }
        catch (FormatException) { return false; }
    }
}
