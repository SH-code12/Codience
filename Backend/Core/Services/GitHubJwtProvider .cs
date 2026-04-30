using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;

namespace Core.Services;

public class GitHubJwtProvider
{
    private readonly IConfiguration _config;

    public GitHubJwtProvider(IConfiguration config)
    {
        _config = config;
    }

    public string GenerateJwt()
    {
        var appId = _config["GitHubAPP:AppId"];
        var pemPath = _config["GitHubAPP:PrivateKeyPath"];

        var pem = File.ReadAllText(pemPath);

        using var rsa = RSA.Create();
        rsa.ImportFromPem(pem.ToCharArray());

        var credentials =
            new SigningCredentials(
                new RsaSecurityKey(rsa),
                SecurityAlgorithms.RsaSha256);

        var now = DateTimeOffset.UtcNow;

        var claims = new List<Claim>
        {
            new Claim(JwtRegisteredClaimNames.Iat,
                now.ToUnixTimeSeconds().ToString(),
                ClaimValueTypes.Integer64)
        };

        var token = new JwtSecurityToken(
            issuer: appId,        // iss
            audience: null,
            claims: claims,
            notBefore: now.UtcDateTime,
            expires: now.AddMinutes(9).UtcDateTime,
            signingCredentials: credentials
        );

        return new JwtSecurityTokenHandler()
            .WriteToken(token);
    }
}