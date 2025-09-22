using System.Text.Json.Serialization;

public class AuthUserDto
{
    [JsonPropertyName("id")]
    public long GitHubId { get; set; } = default!;

    [JsonPropertyName("login")]
    public string UserName { get; set; } = string.Empty;

    [JsonPropertyName("email")]
    public string? Email { get; set; }

    public string AccessToken { get; set; } = string.Empty;
    public string GitHubIdString => GitHubId.ToString();
}
