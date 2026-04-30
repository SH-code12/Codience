namespace Share;

public class WebhookResponseDto
{
    public string EventType { get; set; } = "";
    public string Repository { get; set; } = "";
    public string Action { get; set; } = "";
    public bool Success { get; set; }
}
