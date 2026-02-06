using System.Text.Json.Serialization;

namespace Share;

public class JiraResource
{
    [JsonPropertyName("id")] 
    public string Id { get; set; } = default!;
    [JsonPropertyName("name")]
     public string Name { get; set; } = default!;

}
