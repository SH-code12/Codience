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

    public JiraService(HttpClient httpClient, IConfiguration configuration)
    {
        _httpClient = httpClient;
        _configuration = configuration;
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
        var token = JsonSerializer.Deserialize<JsonElement>(json);

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
        var response = await _httpClient.GetAsync($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/search?jql=project={projectKey}");
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
}