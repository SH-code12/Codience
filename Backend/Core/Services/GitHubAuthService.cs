using System.Net.Http.Headers;
using Core.Abstraction;
using Microsoft.Extensions.Configuration;

using Share;
using System.Net.Http.Json;
using Core.Domain.Models;
using Core.Domain.Contracts;

public class GitHubAuthService : IGithubAuthService
{
    private readonly HttpClient _httpClient;
    private readonly string clientId;
    private readonly string clientSecret;
    private readonly IUnitOfWork _authUow;

    public GitHubAuthService(HttpClient httpClient, IConfiguration configuration, IUnitOfWork authUow)
    {
        _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        clientId = configuration["GitHub:ClientId"]!;
        clientSecret = configuration["GitHub:ClientSecret"]!;
        _authUow = authUow;

    }


    public async Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken = default)
    {


        var req = new HttpRequestMessage(HttpMethod.Post, "https://github.com/login/device/code")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
                {
                    { "client_id", clientId },
                    { "scope", "read:user user:email"}
                })
        };
        req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

        var res = await _httpClient.SendAsync(req, cancellationToken);
        res.EnsureSuccessStatusCode();

        var deviceCode = await res.Content.ReadFromJsonAsync<DeviceCodeResponse>(cancellationToken: cancellationToken);
        return deviceCode ?? throw new Exception("Device code response is null");
    }

    public async Task<AccessTokenResponse> PollForAccessTokenAsync(DeviceCodeResponse deviceCodeResponse, CancellationToken cancellationToken = default)
    {


        var interval = deviceCodeResponse.Interval;
        var expiry = DateTime.UtcNow.AddSeconds(deviceCodeResponse.ExpiresIn);

        while (DateTime.UtcNow < expiry)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var req = new HttpRequestMessage(HttpMethod.Post, "https://github.com/login/oauth/access_token")
            {
                Content = new FormUrlEncodedContent(new Dictionary<string, string>
                    {
                        { "client_id", clientId },
                        { "client_secret", clientSecret },
                        { "device_code", deviceCodeResponse.DeviceCode },
                        { "grant_type", "urn:ietf:params:oauth:grant-type:device_code" }
                    })
            };
            req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

            var res = await _httpClient.SendAsync(req, cancellationToken);
            var json = await res.Content.ReadFromJsonAsync<AccessTokenResponse>(cancellationToken: cancellationToken);

            if (json == null) throw new Exception("Failed to parse access token response");

            if (!string.IsNullOrEmpty(json.AccessToken))
                return json;

            if (json.Error == "authorization_pending")
            {
                await Task.Delay(TimeSpan.FromSeconds(interval), cancellationToken);
                continue;
            }

            if (json.Error == "slow_down")
            {
                interval += 5;
                await Task.Delay(TimeSpan.FromSeconds(interval), cancellationToken);
                continue;
            }

            // أي Error تاني: access_denied, expired_token ...
            return json;
        }

        throw new TimeoutException("Device code expired before authorization.");
    }
        
public async Task<AuthUserDto> SaveUserAsync(string accessToken, CancellationToken ct = default)
{
    if (string.IsNullOrEmpty(accessToken))
        throw new ArgumentException("Access token cannot be null or empty.");

    // ===== التحقق من تهيئة الـ dependencies =====
    if (_httpClient == null) 
        throw new InvalidOperationException("_httpClient is not initialized.");
    if (_authUow == null) 
        throw new InvalidOperationException("_authUow is not initialized.");

    var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();
    if (userRepo == null)
        throw new InvalidOperationException("userRepo is null. Check GetGenericRepository implementation.");

    // ===== إعدادات الـ HttpClient =====
    _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
    _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");

    // ===== جلب بيانات المستخدم من GitHub =====
    var response = await _httpClient.GetAsync("https://api.github.com/user", ct);
    if (!response.IsSuccessStatusCode)
    {
        var errorBody = await response.Content.ReadAsStringAsync(ct);
        throw new Exception($"GitHub API error: {response.StatusCode} - {errorBody}");
    }

    var userDto = await response.Content.ReadFromJsonAsync<AuthUserDto>(cancellationToken: ct);
    if (userDto == null)
        throw new Exception("GitHub user API returned null.");

    var gitHubIdString = userDto.GitHubId.ToString();
    if (string.IsNullOrEmpty(gitHubIdString))
        throw new Exception("GitHubId is null or empty.");

    // ===== التحقق إذا المستخدم موجود بالفعل =====
    var existingUser = await userRepo.FirstOrDefaultAsync(u => u.GitHubId == gitHubIdString);
    if (existingUser != null)
    {
        existingUser.AuthUserName = userDto.UserName ?? existingUser.AuthUserName;
        existingUser.Email = userDto.Email ?? existingUser.Email;
        existingUser.AccessToken = accessToken;

        await _authUow.SaveChangesAsync();

        return new AuthUserDto
        {
            GitHubId = userDto.GitHubId,
            UserName = existingUser.AuthUserName,
            Email = existingUser.Email,
            AccessToken = existingUser.AccessToken
        };
    }

    // ===== إضافة مستخدم جديد =====
    var newUser = new AuthUser
    {
        Id = Guid.NewGuid(),
        GitHubId = gitHubIdString,
        AuthUserName = userDto.UserName ?? "Unknown",
        Email = userDto.Email ?? string.Empty,
        AccessToken = accessToken
    };

    await userRepo.AddAsync(newUser);
    await _authUow.SaveChangesAsync();

    return new AuthUserDto
    {
        GitHubId = userDto.GitHubId,
        UserName = newUser.AuthUserName,
        Email = newUser.Email,
        AccessToken = newUser.AccessToken
    };
}



 
}




