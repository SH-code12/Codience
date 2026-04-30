using System.Net.Http.Headers;
using System.Text.Json;
using Core.Abstraction;
using Share;
using Core.Domain.Contracts;
using Core.Domain.Models;

namespace Core.Services;

public class GithubWebhookService : IGitHubWebhookService
{
    private readonly HttpClient _httpClient;
    private readonly IUnitOfWork _authUow;
    private readonly GitHubJwtProvider _gitHubJwtProvider;
    private readonly IGithubAuthService _gitHubAuthService;
    private readonly IChangeMetricsService _changeMetricsService;
    private readonly IHistoryMetricsService _historyMetricsService;
    private readonly IExperienceMetricsService _experienceMetricsService;


    public GithubWebhookService(
        HttpClient httpClient,
        IUnitOfWork authUow,
        IGithubAuthService gitHubAuthService,
        IChangeMetricsService changeMetricsService,
        IHistoryMetricsService historyMetricsService,
        IExperienceMetricsService experienceMetricsService,
        GitHubJwtProvider gitHubJwtProvider)
    {
        _httpClient = httpClient;
        _authUow = authUow;
        _gitHubAuthService = gitHubAuthService;
        _changeMetricsService = changeMetricsService;
        _historyMetricsService = historyMetricsService;
        _experienceMetricsService = experienceMetricsService;
        _gitHubJwtProvider = gitHubJwtProvider;
    }

    // ==============================
  
    public Task<WebhookResponseDto> HandleWebhookAsync(string eventType, string payload)
    {
        using var doc = JsonDocument.Parse(payload);

        var repo = doc.RootElement
            .GetProperty("repository")
            .GetProperty("name")
            .GetString() ?? "";

        var action = doc.RootElement.TryGetProperty("action", out var act)
            ? act.GetString() ?? ""
            : "";

        return Task.FromResult(new WebhookResponseDto
        {
            EventType = eventType,
            Repository = repo,
            Action = action,
            Success = true
        });
    }

    // ==============================
    // INSTALLATION ID
    // ==============================
    public async Task<long?> GetInstallationIdAsync(string owner, string repo)
    {
        var jwt = _gitHubJwtProvider.GenerateJwt();

        var req = new HttpRequestMessage(
            HttpMethod.Get,
            $"https://api.github.com/repos/{owner}/{repo}/installation");

        req.Headers.UserAgent.ParseAdd("Codience");
        req.Headers.Authorization =
            new AuthenticationHeaderValue("Bearer", jwt);
        req.Headers.Accept.ParseAdd("application/vnd.github+json");

        var res = await _httpClient.SendAsync(req);

        if (!res.IsSuccessStatusCode)
            return null;

        var json = await res.Content.ReadAsStringAsync();
        using var doc = JsonDocument.Parse(json);

        return doc.RootElement.GetProperty("id").GetInt64();
    }

    // ==============================
    // DISCONNECT
    // ==============================
    public async Task DisconnectRepositoryAsync(string owner, string repo)
    {
        var id = await GetInstallationIdAsync(owner, repo);

        if (id == null)
            return;

        Console.WriteLine($"Disconnected repo: {repo}");
    }

    // ==============================
    // MAIN METRICS EVENT HANDLER
    // ==============================
    public async Task<WebhookMetrics?> HandleEventAsync(string eventType, string payload)
    {
        if (eventType != "pull_request")
            return null;

        using var doc = JsonDocument.Parse(payload);
        var root = doc.RootElement;

        var action = root.GetProperty("action").GetString();

        if (action is not ("opened" or "synchronize" or "reopened"))
            return null;

        var repoElement = root.GetProperty("repository");

        var owner = repoElement.GetProperty("owner").GetProperty("login").GetString() ?? "";
        var repo = repoElement.GetProperty("name").GetString() ?? "";

        var pullNumber = root.GetProperty("number").GetInt32();
    
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);
        var changeMetrics = _changeMetricsService.Calculate(files);

        var historyMetrics = await _historyMetricsService.Calculate(owner, repo, pullNumber);

        var experienceMetrics = await _experienceMetricsService
            .CalculateExperienceMetrics(owner, repo, pullNumber);

        return new WebhookMetrics
        {
            ChangeMetrics = changeMetrics,
            HistoryMetrics = historyMetrics,
            ExperienceMetrics = experienceMetrics
        };
    }

}