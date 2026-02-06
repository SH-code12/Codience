using System.Text.Json.Serialization;

namespace Share;

public class JiraAccessTokenResponse
{
    [JsonPropertyName("access_token")] 
    public string AccessToken { get; set; } = default!;
    
    [JsonPropertyName("expires_in")] 
    public int ExpiresIn { get; set; }
}

