using System.Text.Json;

namespace Core.Abstraction;

public interface IJiraService
{
    Task<string> ExchangeCodeForAdminToken(string code);
    Task<JsonElement> GetAccessibleResources(string accessToken);
    Task<JsonElement> GetAllProjects(string accessToken, string cloudId);
    Task<JsonElement> GetIssues(string accessToken, string cloudId, string projectKey);
    Task<JsonElement> GetProjectRoles(string accessToken, string cloudId, string projectKey);
}