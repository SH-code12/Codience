using System.Net.Http.Headers;
using Core.Abstraction;
using Microsoft.Extensions.Configuration;

using Share;
using System.Net.Http.Json;

public class GitHubAuthService : IGithubAuthService
{
     private readonly HttpClient _httpClient;
    private readonly string clientId;
    private readonly string clientSecret;

    public GitHubAuthService(HttpClient httpClient, IConfiguration configuration)
    {
        _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        clientId = configuration["GitHub:ClientId"]!;
        clientSecret = configuration["ClientSecret"]!;

    }

    
        public async Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken = default)
        {
            

            var req = new HttpRequestMessage(HttpMethod.Post, "https://github.com/login/device/code")
            {
                Content = new FormUrlEncodedContent(new Dictionary<string, string>
                {
                    { "client_id", clientId },
                    { "scope", "repo" } 
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

 
}




