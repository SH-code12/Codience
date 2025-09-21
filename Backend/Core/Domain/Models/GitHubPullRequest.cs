namespace Core.Domain.Models;

public class GitHubPullRequest : BaseEntity<int>
{
    public int UserId{get;set;}=default!;
    public string Title { get; set; } = default!;
    public string HtmlUrl { get; set; } = default!;
    public string State { get; set; } = default!;
    public string CreatedAt { get; set; } = default!;
     public int RepositoryId { get; set; }
    public GitHubRepo Repository { get; set; } = null!;
}
