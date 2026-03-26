using System.Text.Json.Serialization;

namespace Core.Domain.Models;

public class ReviewerRequest
{
    [JsonPropertyName("owner")]
    public string Owner { get; set; }

    [JsonPropertyName("repo")]
    public string Repo { get; set; }

    [JsonPropertyName("pr_number")] // This MUST match app.py exactly
    public int PrNumber { get; set; }
}