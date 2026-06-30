using Core.Domain.Models;
using Core.Domain.Contracts;
using Core.Abstraction;
using Microsoft.Extensions.Configuration;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Share;

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
        if (!response.IsSuccessStatusCode) throw new Exception("Jira OAuth Error: " + json);
        var token = JsonSerializer.Deserialize<JsonElement>(json);

        if (!token.TryGetProperty("access_token", out var accessToken))
            throw new Exception("access_token not found in response: " + json);

        return accessToken.GetString()!;
    }

    public async Task<JsonElement> GetAccessibleResources(string accessToken)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync("https://api.atlassian.com/oauth/token/accessible-resources");
        var json = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode) throw new Exception("AccessibleResources Error: " + json);
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    public async Task<JsonElement> GetAllProjects(string accessToken, string cloudId)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync("https://api.atlassian.com/ex/jira/" + cloudId + "/rest/api/3/project");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    public async Task<JsonElement> GetIssues(string accessToken, string cloudId, string projectKey)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var url = "https://api.atlassian.com/ex/jira/" + cloudId + "/rest/api/3/search/jql";
        var body = new { jql = "project=" + projectKey };
        var response = await _httpClient.PostAsJsonAsync(url, body);
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    public async Task<JsonElement> GetProjectRoles(string accessToken, string cloudId, string projectKey)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync("https://api.atlassian.com/ex/jira/" + cloudId + "/rest/api/3/project/" + projectKey + "/role");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<JsonElement>(json);
    }

    public async Task SaveJiraIssuesAsync(string userName, string cloudId, string projectKey, JsonElement issuesJson)
    {
        var userRepo = _unitOfWork.GetGenericRepository<AuthUser, Guid>();
        var user = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == userName);
        if (user == null) return;
        if (!issuesJson.TryGetProperty("issues", out var issuesArray)) return;
        var issueRepo = _unitOfWork.GetGenericRepository<JiraIssue, int>();
        foreach (var issueData in issuesArray.EnumerateArray())
        {
            if (!issueData.TryGetProperty("key", out var keyProp)) continue;
            var key = keyProp.GetString()!;
            if (!issueData.TryGetProperty("fields", out var fields)) continue;
            var summary = fields.TryGetProperty("summary", out var s) ? s.GetString() ?? "No Summary" : "No Summary";
            var existingIssue = await issueRepo.FirstOrDefaultAsync(i => i.JiraKey == key && i.UserId == user.Id);
            if (existingIssue == null) {
                await issueRepo.AddAsync(new JiraIssue { JiraKey = key, Summary = summary, UserId = user.Id });
            }
        }
        await _unitOfWork.SaveChangesAsync();
    }

    public async Task<IEnumerable<JiraIssueDto>> GetAssignedIssuesAsync(string accessToken, string cloudId, string projectKey, string assigneeName)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        
        // Use the mandatory /search/jql endpoint
        var jql = $"project = '{projectKey}' AND assignee = '{assigneeName}'";
        var url = $"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/search/jql";
        
        // CRITICAL: Request explicit fields so the API returns full data instead of just IDs
        var body = new { 
            jql = jql,
            fields = new[] { "summary", "status", "priority", "issuetype", "description" }
        };
        
        var response = await _httpClient.PostAsJsonAsync(url, body);
        var json = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode) throw new Exception("Jira Search Error: " + json);
        
        var result = JsonSerializer.Deserialize<JsonElement>(json);
        var list = new List<JiraIssueDto>();

        if (result.TryGetProperty("issues", out var issuesArray) && issuesArray.ValueKind == JsonValueKind.Array) {
            foreach (var issue in issuesArray.EnumerateArray()) {
                try {
                    if (!issue.TryGetProperty("key", out var keyProp)) continue;
                    if (!issue.TryGetProperty("fields", out var fields)) continue;

                    list.Add(new JiraIssueDto {
                        Key = keyProp.GetString()!,
                        Summary = fields.TryGetProperty("summary", out var s) ? s.GetString() ?? "No Summary" : "No Summary",
                        Status = fields.TryGetProperty("status", out var st) && st.TryGetProperty("name", out var stn) 
                                 ? stn.GetString() ?? "Unknown" 
                                 : "Unknown",
                        Priority = fields.TryGetProperty("priority", out var p) && p.ValueKind != JsonValueKind.Null && p.TryGetProperty("name", out var pn) 
                                   ? pn.GetString() ?? "Medium" 
                                   : "Medium",
                        IssueType = fields.TryGetProperty("issuetype", out var it) && it.TryGetProperty("name", out var itn) 
                                     ? itn.GetString() ?? "Task" 
                                     : "Task",
                        Description = fields.TryGetProperty("description", out var d) ? d.ToString() : ""
                    });
                } catch (Exception ex) {
                    Console.WriteLine("Error parsing issue: " + ex.Message);
                }
            }
        }
        return list;
    }

    public async Task<bool> AssignIssueAsync(string accessToken, string cloudId, string issueKey, string accountId)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var body = new { accountId = accountId };
        var response = await _httpClient.PutAsJsonAsync("https://api.atlassian.com/ex/jira/" + cloudId + "/rest/api/3/issue/" + issueKey + "/assignee", body);
        if (!response.IsSuccessStatusCode) {
            var json = await response.Content.ReadAsStringAsync();
            throw new Exception("AssignIssue Error: " + json);
        }
        return true;
    }

    public async Task<JiraUserProfile> GetCurrentUserAsync(string accessToken)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        var response = await _httpClient.GetAsync("https://api.atlassian.com/me");
        var json = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode) throw new Exception("GetCurrentUser Error: " + json);
        return JsonSerializer.Deserialize<JiraUserProfile>(json)!;
    }
    public async Task<IEnumerable<JiraIssueDto>> GetProjectIssuesAsync(
    string accessToken,
    string cloudId,
    string projectKey)
{
    _httpClient.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", accessToken);

    var url = $"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/search/jql";

    var body = new
    {
        jql = $"project = '{projectKey}'",
        fields = new[]
        {
            "summary",
            "status",
            "priority",
            "issuetype",
            "description"
        }
    };

    var response = await _httpClient.PostAsJsonAsync(url, body);
    var json = await response.Content.ReadAsStringAsync();

    if (!response.IsSuccessStatusCode)
        throw new Exception("Jira Search Error: " + json);

    var result = JsonSerializer.Deserialize<JsonElement>(json);
    var list = new List<JiraIssueDto>();

    if (result.TryGetProperty("issues", out var issuesArray))
    {
        foreach (var issue in issuesArray.EnumerateArray())
        {
            var fields = issue.GetProperty("fields");

            list.Add(new JiraIssueDto
            {
                Key = issue.GetProperty("key").GetString()!,
                Summary = fields.TryGetProperty("summary", out var s)
                    ? s.GetString() ?? "No Summary"
                    : "No Summary",

                Status = fields.TryGetProperty("status", out var st)
                    ? st.GetProperty("name").GetString() ?? "Unknown"
                    : "Unknown",

                Priority = fields.TryGetProperty("priority", out var p) &&
                           p.ValueKind != JsonValueKind.Null
                    ? p.GetProperty("name").GetString() ?? "Medium"
                    : "Medium",

                IssueType = fields.TryGetProperty("issuetype", out var it)
                    ? it.GetProperty("name").GetString() ?? "Task"
                    : "Task",

                Description = fields.TryGetProperty("description", out var d)
                    ? d.ToString()
                    : ""
            });
        }
    }

    return list;
}
}
