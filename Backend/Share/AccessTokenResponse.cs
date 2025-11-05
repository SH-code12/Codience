using System.Text.Json.Serialization;
public record AccessTokenResponse
{
    [JsonPropertyName("access_token")]
     string? AccessToken { get; set; }

    [JsonPropertyName("token_type")]
   string? TokenType { get; set; }

    [JsonPropertyName("scope")]
    public string? Scope { get; set; }

    [JsonPropertyName("error")]
    public string? Error { get; set; }

    [JsonPropertyName("error_description")]
    public string? ErrorDescription { get; set; }
}
