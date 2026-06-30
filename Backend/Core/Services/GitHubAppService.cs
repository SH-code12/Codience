// ===============================
// File: Core.Services/GitHubAppService.cs
// ===============================
using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Microsoft.Extensions.Configuration;
using Share;

namespace Core.Services;

public class GitHubAppService : IGitHubAppService
{
    private readonly HttpClient _httpClient;
    private readonly GitHubJwtProvider _jwtProvider;
    private readonly IConfiguration _config;
    private readonly IUnitOfWork _authUow;

    public GitHubAppService(
        HttpClient httpClient,
        GitHubJwtProvider jwtProvider,
        IConfiguration config,
        IUnitOfWork authUow)
    {
        _httpClient = httpClient;
        _jwtProvider = jwtProvider;
        _config = config;
        _authUow = authUow;
    }

    // =========================
    // JWT headers (App auth)
    // =========================
    private void AddJwtHeaders()
    {
        _httpClient.DefaultRequestHeaders.Clear();

        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue(
                "Bearer",
                _jwtProvider.GenerateJwt());

        _httpClient.DefaultRequestHeaders.Accept.Add(
            new MediaTypeWithQualityHeaderValue(
                "application/vnd.github+json"));

        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("CodienceApp");
    }

    // =========================
    // GET /app
    // =========================
    public async Task<GitHubAppDto> GetAuthenticatedAppAsync()
    {
        AddJwtHeaders();

        var res =
            await _httpClient.GetAsync("https://api.github.com/app");

        await EnsureSuccess(res);

        var json = await res.Content.ReadAsStringAsync();

        return JsonSerializer.Deserialize<GitHubAppDto>(
            json,
            JsonOptions())!;
    }

    // =========================
    // GET installations
    // =========================
    public async Task<IReadOnlyList<GitHubInstallationDto>>
        GetInstallationsAsync(int page = 1, int perPage = 30)
    {
        AddJwtHeaders();

        var res =
            await _httpClient.GetAsync(
                $"https://api.github.com/app/installations?page={page}&per_page={perPage}");

        await EnsureSuccess(res);

        var json = await res.Content.ReadAsStringAsync();

        return JsonSerializer.Deserialize<List<GitHubInstallationDto>>(
                   json,
                   JsonOptions())
               ?? new List<GitHubInstallationDto>();
    }

    // =========================
    // GET repo installation
    // =========================
    public async Task<GitHubInstallationDto?> GetRepositoryInstallationAsync(
        string owner,
        string repo)
    {
        AddJwtHeaders();

        var res =
            await _httpClient.GetAsync(
                $"https://api.github.com/repos/{owner}/{repo}/installation");

        if (res.StatusCode == HttpStatusCode.NotFound)
            return null;

        await EnsureSuccess(res);

        var json = await res.Content.ReadAsStringAsync();

        return JsonSerializer.Deserialize<GitHubInstallationDto>(
            json,
            JsonOptions());
    }

    // =========================
    // CHECK installed
    // =========================
    public async Task<bool> IsInstalledAsync(string owner, string repo)
    {
        return await GetRepositoryInstallationAsync(owner, repo) != null;
    }

    // =========================
    // CHECK admin
    // =========================
    public async Task<bool> IsUserAdminAsync(
        string userName,
        string owner,
        string repo)
    {
        var repoUser =
            _authUow.GetGenericRepository<AuthUser, Guid>();

        var user =
            await repoUser.FirstOrDefaultAsync(x => x.AuthUserName == userName);

        if (user == null)
            throw new Exception("User not found");

        var req = new HttpRequestMessage(
            HttpMethod.Get,
            $"https://api.github.com/repos/{owner}/{repo}");

        req.Headers.UserAgent.ParseAdd("CodienceApp");
        req.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", user.AccessToken);

        var res = await _httpClient.SendAsync(req);
        await EnsureSuccess(res);

        var json = await res.Content.ReadAsStringAsync();

        using var doc = JsonDocument.Parse(json);

        return doc.RootElement
            .GetProperty("permissions")
            .GetProperty("admin")
            .GetBoolean();
    }

    // =========================
    // MAIN FLOW (IMPORTANT)
    // =========================
    public async Task<ConnectRepoResponseDto> ConnectRepositoryAsync(string userName,string owner,string repo)
    {
        var installed =
            await IsInstalledAsync(owner, repo);

        if (installed)
        {
            return new ConnectRepoResponseDto
            {
                IsInstalled = true,
                IsAdmin = true,
                Message = "App already installed"
            };
        }

        var isAdmin =
            await IsUserAdminAsync(userName, owner, repo);

        if (!isAdmin)
        {
            return new ConnectRepoResponseDto
            {
                IsInstalled = false,
                IsAdmin = false,
                Message = "User is not admin"
            };
        }

        return new ConnectRepoResponseDto
        {
            IsInstalled = false,
            IsAdmin = true,
            InstallUrl = GetInstallUrl(owner),
            Message = "Installation required"
        };
    }

    // =========================
    // INSTALL URL
    // =========================
    public string GetInstallUrl(string owner)
    {
        var slug = _config["GitHubAPP:AppSlug"];

        return
            $"https://github.com/apps/{slug}/installations/new?target_id={owner}";
    }

    public Task<string> GetInstallUrlAsync(string owner)
        => Task.FromResult(GetInstallUrl(owner));

    // =========================
    // INSTALLATION TOKEN
    // =========================
    public async Task<string> CreateInstallationTokenAsync(long installationId)
    {
        AddJwtHeaders();

        var res =
            await _httpClient.PostAsync(
                $"https://api.github.com/app/installations/{installationId}/access_tokens",
                new StringContent("{}", Encoding.UTF8, "application/json"));

        await EnsureSuccess(res);

        var json = await res.Content.ReadAsStringAsync();

        using var doc = JsonDocument.Parse(json);

        return doc.RootElement.GetProperty("token").GetString()!;
    }

    public async Task<IReadOnlyList<GitHubPullRequestDto>> GetPullRequestsAsync(long? repositoryId)
    {
        if (repositoryId is null)
        {
            return new List<GitHubPullRequestDto>();
        }

        AddJwtHeaders();
        var repoRes = await _httpClient.GetAsync($"https://api.github.com/repositories/{repositoryId}");
        await EnsureSuccess(repoRes);
        var repoJson = await repoRes.Content.ReadAsStringAsync();
        using var repoDoc = JsonDocument.Parse(repoJson);
        var owner = repoDoc.RootElement.GetProperty("owner").GetProperty("login").GetString()!;
        var repo = repoDoc.RootElement.GetProperty("name").GetString()!;

        var installation = await GetRepositoryInstallationAsync(owner, repo);
        if (installation is null)
        {
            return new List<GitHubPullRequestDto>();
        }
        var token = await CreateInstallationTokenAsync(installation.Id);

        _httpClient.DefaultRequestHeaders.Clear();
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github+json"));
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("CodienceApp");

        var prsRes = await _httpClient.GetAsync($"https://api.github.com/repos/{owner}/{repo}/pulls");
        await EnsureSuccess(prsRes);
        var prsJson = await prsRes.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<List<GitHubPullRequestDto>>(prsJson, JsonOptions()) ?? new List<GitHubPullRequestDto>();
    }

    // =========================
    // DELETE installation
    // =========================
    public async Task DeleteInstallationAsync(long installationId)
    {
        AddJwtHeaders();

        var res =
            await _httpClient.DeleteAsync(
                $"https://api.github.com/app/installations/{installationId}");

        await EnsureSuccess(res);
    }

    // =========================
    // helpers
    // =========================
    private static async Task EnsureSuccess(HttpResponseMessage res)
    {
        if (res.IsSuccessStatusCode)
            return;

        var body = await res.Content.ReadAsStringAsync();

        throw new Exception($"GitHub API Error: {(int)res.StatusCode} - {body}");
    }

    private static JsonSerializerOptions JsonOptions()
        => new()
        {
            PropertyNameCaseInsensitive = true
        };
}