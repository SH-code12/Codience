using Core.Domain.Models;

public class JiraIssue : BaseEntity<int>
{
    public string JiraKey { get; set; } = default!;
    public string Summary { get; set; } = default!;
    public string Status { get; set; } = default!;
    public string Priority { get; set; } = default!;
    public string IssueType { get; set; } = default!;

    public Guid UserId { get; set; }
    public AuthUser User { get; set; } = default!;

    public ICollection<GitHubPullRequest> PullRequests { get; set; }
        = new List<GitHubPullRequest>();
}
