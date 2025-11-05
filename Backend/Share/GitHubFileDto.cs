using System.Text.Json.Serialization;

public record GitHubFileDto
(
    [property: JsonPropertyName("filename")] string Filename,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("additions")] int Additions,
    [property: JsonPropertyName("deletions")] int Deletions,
    [property: JsonPropertyName("changes")] int Changes,
    [property: JsonPropertyName("blob_url")] string BlobUrl,
    [property: JsonPropertyName("raw_url")] string RawUrl
);