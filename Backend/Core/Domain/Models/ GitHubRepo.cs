namespace Core.Domain.Models;

public class GitHubRepo :BaseEntity<int>
{

    public string Name { get; set; } = default!;
    public string HtmlUrl { get; set; } = default!;
    public string? Description { get; set; } = default!;
    public int UserId{get;set;}
    public ICollection<GitHubPullRequest>? PullRequests { get; set; } = new List<GitHubPullRequest>();
}


