namespace Share;

public class JiraIssueDto
{
    public string Key { get; set; } = default!;
    public string Summary { get; set; } = default!;
    public string? Description { get; set; }
    public string Status { get; set; } = default!;
    public string Priority { get; set; } = default!;
    public string IssueType { get; set; } = default!;
}
