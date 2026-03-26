using System.Text.Json.Serialization;

namespace Share;

public class JiraSearchResponse
{
    [JsonPropertyName("issues")]
    public List<JiraApiIssue> Issues { get; set; } = new();
}
