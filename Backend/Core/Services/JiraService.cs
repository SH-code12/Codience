using Core.Domain.Models;
using Core.Domain.Contracts;
using Core.Abstraction;
using Microsoft.Extensions.Configuration;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;

namespace Core.Services;

public class JiraService : IJiraService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly IUnitOfWork _unitOfWork;

    public JiraService(HttpClient httpClient, IConfiguration configuration, IUnitOfWork unitOfWork)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _unitOfWork = unitOfWork;
    }

    // Exchange code for Admin access token
    public async Task<string> ExchangeCodeForAdminToken(string code)
    {
        var body = new
        {
            grant_type = "authorization_code",
            client_id = _configuration["Jira:ClientId"],
            client_secret = _configuration["Jira:ClientSecret"],
            code = code,
            redirect_uri = _configuration["Jira:CallbackUrl"]
        };

        var response = await _httpClient.PostAsJsonAsync("https://auth.atlassian.com/oauth/token", body);
        var json = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode) throw new Exception($"Jira OAuth Error: {json}"); var token = JsonSerializer.Deserialize<JsonElement>(json);

        if (!token.TryGetProperty("access_token", out var accessToken))
            throw new Exception($"Token Error: {json}");

        return accessToken.GetString()!;
    }

    // Get all accessible Jira sites
    public async Task<JsonElement> GetAccessibleResources(string accessToken)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync("https://api.atlassian.com/oauth/token/accessible-resources");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    // Get all projects (Classic + Next-gen) for Admin
    public async Task<JsonElement> GetAllProjects(string accessToken, string cloudId)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);

        // 1️⃣ Classic projects
        var response1 = await _httpClient.GetAsync($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/project");
        var json1 = await response1.Content.ReadAsStringAsync();
        var projects = JsonSerializer.Deserialize<JsonElement>(json1);

        if (projects.ValueKind == JsonValueKind.Array && projects.GetArrayLength() > 0)
            return projects;

        // 2️⃣ Fallback Next-gen
        var response2 = await _httpClient.GetAsync($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/project/search");
        var json2 = await response2.Content.ReadAsStringAsync();
        var projectsNext = JsonSerializer.Deserialize<JsonElement>(json2);

        if (projectsNext.ValueKind == JsonValueKind.Object && projectsNext.TryGetProperty("values", out var values))
            return values;

        return projectsNext; // might be empty
    }

    // Get issues for a project
    public async Task<JsonElement> GetIssues(string accessToken, string cloudId, string projectKey)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/search/jql?jql=project={projectKey}");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    // Get roles for a project
    public async Task<JsonElement> GetProjectRoles(string accessToken, string cloudId, string projectKey)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/project/{projectKey}/role");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    public async Task SaveJiraIssuesAsync(string userName, string cloudId, string projectKey, JsonElement issuesJson)
    {
        var userRepo = _unitOfWork.GetGenericRepository<AuthUser, Guid>();
        var user = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == userName);
        if (user == null) return;

        if (!issuesJson.TryGetProperty("issues", out var issuesArray) || issuesArray.ValueKind != JsonValueKind.Array)
            return;

        var issueRepo = _unitOfWork.GetGenericRepository<JiraIssue, int>();

        foreach (var issueData in issuesArray.EnumerateArray())
        {
            var key = issueData.GetProperty("key").GetString()!;
            var fields = issueData.GetProperty("fields");
            var summary = fields.GetProperty("summary").GetString() ?? "No Summary";
            var status = fields.GetProperty("status").GetProperty("name").GetString() ?? "Unknown";
            var priority = fields.TryGetProperty("priority", out var p) ? p.GetProperty("name").GetString() ?? "Medium" : "Medium";
            var issueType = fields.GetProperty("issuetype").GetProperty("name").GetString() ?? "Task";

            var existingIssue = await issueRepo.FirstOrDefaultAsync(i => i.JiraKey == key && i.UserId == user.Id);
            if (existingIssue == null)
            {
                await issueRepo.AddAsync(new JiraIssue
                {
                    JiraKey = key,
                    Summary = summary,
                    Status = status,
                    Priority = priority,
                    IssueType = issueType,
                    UserId = user.Id
                });
            }
            else
            {
                existingIssue.Summary = summary;
                existingIssue.Status = status;
                existingIssue.Priority = priority;
                existingIssue.IssueType = issueType;
            }
        }

        await _unitOfWork.SaveChangesAsync();
    }

    public async Task<JsonElement> GetAssignedIssuesAsync(string accessToken, string cloudId, string projectKey, string assigneeName)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var jql = $"project={projectKey} AND assignee='{assigneeName}'";
        var encodedJql = Uri.EscapeDataString(jql); var response = await _httpClient.GetAsync($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/search/jql?jql={encodedJql}");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }
}
