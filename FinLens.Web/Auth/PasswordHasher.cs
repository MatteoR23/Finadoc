using Microsoft.AspNetCore.Cryptography.KeyDerivation;
using System.Security.Cryptography;

namespace FinLens.Web.Auth;

public static class PasswordHasher
{
    private const int SaltSize = 16;        // 128-bit salt
    private const int HashSize = 64;        // 512-bit output
    private const int Iterations = 310_000; // OWASP 2023 recommendation for PBKDF2-SHA512

    /// <summary>
    /// Hashes a password using PBKDF2-SHA512 with a random salt.
    /// Returns a self-contained string in the format "base64(salt):base64(hash)".
    /// </summary>
    public static string HashPassword(string password)
    {
        var salt = RandomNumberGenerator.GetBytes(SaltSize);
        var hash = KeyDerivation.Pbkdf2(
            password: password,
            salt: salt,
            prf: KeyDerivationPrf.HMACSHA512,
            iterationCount: Iterations,
            numBytesRequested: HashSize);

        return $"{Convert.ToBase64String(salt)}:{Convert.ToBase64String(hash)}";
    }

    /// <summary>
    /// Verifies a plaintext password against a stored hash produced by <see cref="HashPassword"/>.
    /// Uses a constant-time comparison to prevent timing attacks.
    /// </summary>
    public static bool VerifyPassword(string password, string storedHash)
    {
        var parts = storedHash.Split(':');
        if (parts.Length != 2) return false;

        byte[] salt, expectedHash;
        try
        {
            salt = Convert.FromBase64String(parts[0]);
            expectedHash = Convert.FromBase64String(parts[1]);
        }
        catch (FormatException)
        {
            return false;
        }

        var actualHash = KeyDerivation.Pbkdf2(
            password: password,
            salt: salt,
            prf: KeyDerivationPrf.HMACSHA512,
            iterationCount: Iterations,
            numBytesRequested: HashSize);

        return CryptographicOperations.FixedTimeEquals(actualHash, expectedHash);
    }
}
