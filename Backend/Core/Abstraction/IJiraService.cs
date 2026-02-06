using Share;

namespace Core.Abstraction;

public interface IJiraService
{
    
    Task<JiraAccessTokenResponse> GetAccessTokenAsync(string code, CancellationToken ct = default);
    Task<string> GetJiraAccountIdAsync(string accessToken, CancellationToken ct = default);
    Task SaveJiraUserAsync(Guid userId, string jiraAccountId, string accessToken);
}

