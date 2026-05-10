namespace Share;

public class JiraRequestDto
{
    public string Token { get; set; } = default!;
    public string CloudId { get; set; } = default!;
    public string ProjectKey { get; set; } = default!;
    public string AssigneeName { get; set; } = default!;
}
