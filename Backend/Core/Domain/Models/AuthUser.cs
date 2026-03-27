

namespace Core.Domain.Models;


public class AuthUser : BaseEntity<Guid>
{


        public string GitHubId { get; set; } = default!;
        public string AuthUserName { get; set; } = default!;
        public string Email { get; set; } = default!;
        public string? AccessToken { get; set; } = default!;
        public string? Password { get; set; } = default!;
        public string? JiraAccountId { get; set; } = default!;
        public string? JiraAccessToken { get; set; } = default!;
        public ICollection<GitHubRepo> Repositories { get; set; } = new List<GitHubRepo>();
        public ICollection<GitHubPullRequest> PullRequests { get; set; } = new List<GitHubPullRequest>();
        public ICollection<JiraIssue> JiraIssues { get; set; } = new List<JiraIssue>();

    
}
