using System.Text.Json.Serialization;

namespace Share;

public class JiraApiFields
{
     [JsonPropertyName("summary")]
    public string Summary { get; set; } = default!;

    [JsonPropertyName("status")]
    public JiraApiNamed Status { get; set; } = default!;

    [JsonPropertyName("priority")]
    public JiraApiNamed Priority { get; set; } = default!;

    [JsonPropertyName("issuetype")]
    public JiraApiNamed IssueType { get; set; } = default!;
}
