using System.Text.Json.Serialization;

namespace Share;

public class JiraUserProfile
{
    [JsonPropertyName("account_id")]
    public string AccountId { get; set; } = default!;
    
    [JsonPropertyName("name")]
    public string Name { get; set; } = default!;

    [JsonPropertyName("email")]
    public string Email { get; set; } = default!;
}