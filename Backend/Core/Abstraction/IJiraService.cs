using System.Text.Json;
using Share;

namespace Core.Abstraction;

public interface IJiraService
{
    Task<string> ExchangeCodeForAdminToken(string code);
    Task<JsonElement> GetAccessibleResources(string accessToken);
    Task<JsonElement> GetAllProjects(string accessToken, string cloudId);
    Task<JsonElement> GetIssues(string accessToken, string cloudId, string projectKey);
    Task<JsonElement> GetProjectRoles(string accessToken, string cloudId, string projectKey);
    Task SaveJiraIssuesAsync(string userName, string cloudId, string projectKey, JsonElement issuesJson);
    Task<IEnumerable<JiraIssueDto>> GetAssignedIssuesAsync(string accessToken, string cloudId, string projectKey, string assigneeName);
    Task<bool> AssignIssueAsync(string accessToken, string cloudId, string issueKey, string accountId);
    Task<JiraUserProfile> GetCurrentUserAsync(string accessToken);
}
