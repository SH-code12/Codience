using System.Text.Json.Serialization;

namespace Share;

public class JiraApiNamed
{
     [JsonPropertyName("name")]
    public string Name { get; set; } = default!;
}
