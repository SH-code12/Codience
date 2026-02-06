namespace Core.Domain.Models;

public class JiraIssue : BaseEntity<int>
{

    public required string JiraKey { get; set; }
    public string IssueType { get; set; } = default!; 
    public ICollection<GitHubPullRequest> PullRequests { get; set; } = new List<GitHubPullRequest>();
}

