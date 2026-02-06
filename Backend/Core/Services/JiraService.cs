using System.Net.Http.Json;
using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Microsoft.Extensions.Configuration;
using Share;

namespace Core.Services;

public class JiraService: IJiraService
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly IUnitOfWork _UnitOfWork;

    public JiraService(HttpClient httpClient, IConfiguration configuration, IUnitOfWork uow)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _UnitOfWork = uow;
    }

    public async Task<JiraAccessTokenResponse> GetAccessTokenAsync(string code, CancellationToken ct = default)
    {
        var payload = new {
            grant_type = "authorization_code",
            client_id = _configuration["Jira:ClientId"],
            client_secret = _configuration["Jira:ClientSecret"],
            code = code,
            redirect_uri = _configuration["Jira:CallbackUrl"]
        };
        var res = await _httpClient.PostAsJsonAsync("https://auth.atlassian.com/oauth/token", payload, ct);
        return await res.Content.ReadFromJsonAsync<JiraAccessTokenResponse>(cancellationToken: ct) ?? throw new Exception();
    }

    public async Task<string> GetJiraAccountIdAsync(string accessToken, CancellationToken ct = default)
    {
        _httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", accessToken);
        // 1.Cloud ID
        var resources = await _httpClient.GetFromJsonAsync<List<JiraResource>>("https://api.atlassian.com/oauth/token/accessible-resources", ct);
        var cloudId = resources?.FirstOrDefault()?.Id ?? throw new Exception("Cloud ID not found");

        // 2.Account ID
        var profile = await _httpClient.GetFromJsonAsync<JiraUserProfile>($"https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/myself", ct);
        return profile!.AccountId;
    }

    public async Task SaveJiraUserAsync(Guid userId, string jiraAccountId, string accessToken)
    {
        var userRepo = _UnitOfWork.GetGenericRepository<AuthUser, Guid>();
        var user = await userRepo.FirstOrDefaultAsync(u => u.Id == userId);
        if (user != null) {
            user.JiraAccountId = jiraAccountId;
            await _UnitOfWork.SaveChangesAsync();
        }
    }
}

