using System.ComponentModel.Design.Serialization;
using System.Text.Json.Serialization;

namespace Core.Domain.Models;

public class GitHubPullRequest : BaseEntity<int>
{
    public Guid UserId{get;set;}=default!;

    public AuthUser User { get; set; } = default!;
     public long GitHubId { get; set; }

    public long Number { get; set; } = default;
    public string Title { get; set; } = default!;
    public string HtmlUrl { get; set; } = default!;
    public string State { get; set; } = default!;
    public DateTime CreatedAt { get; set; } = default!;
     public int RepositoryId { get; set; }
    public GitHubRepo Repository { get; set; } = null!;
}
