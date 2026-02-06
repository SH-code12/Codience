using System.Text.Json.Serialization;

namespace Share;

public class JiraUserProfile
{
    [JsonPropertyName("accountId")]
     public string AccountId { get; set; } = default!;
    [JsonPropertyName("displayName")] public string DisplayName { get; set; } = default!;
}
