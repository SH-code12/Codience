using System.Text.Json;

namespace Share;

public class JiraAuthResponseDto
{
    public string AccessToken { get; set; } = default!;
    public string CloudId { get; set; } = default!;
    public JsonElement Projects { get; set; }
}
