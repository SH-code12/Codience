namespace Core.Domain.Models;

public class GitHubRepo :BaseEntity<int>
{

    public string Name { get; set; } = default!;
    public string FullName { get; set; } = default!;
    public bool Private {get;set;}
    public string HtmlUrl { get; set; } = default!;
    public string? Description { get; set; } = default!;
    public Guid UserId{get;set;}

    public AuthUser User { get; set; } = default!;
    public ICollection<GitHubPullRequest>? PullRequests { get; set; } = new List<GitHubPullRequest>();
}


