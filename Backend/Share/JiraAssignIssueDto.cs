namespace Share;

public class JiraAssignIssueDto
{
    public string Token { get; set; } = default!;
    public string CloudId { get; set; } = default!;
    public string IssueKey { get; set; } = default!;
    public string AccountId { get; set; } = default!;
}
