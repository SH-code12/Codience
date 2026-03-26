using System.Text.Json.Serialization;

namespace Share;

public class JiraApiIssue
{
     [JsonPropertyName("key")]
    public string Key { get; set; } = default!;

    [JsonPropertyName("fields")]
    public JiraApiFields Fields { get; set; } = default!;
}
