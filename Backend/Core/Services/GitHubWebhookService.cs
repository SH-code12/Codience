using Core.Abstraction;
using Share;
using System.Text.Json;

namespace Core.Services;

public class GitHubWebhookService : IGitHubWebhookService
{
    private readonly IChangeMetricsService _changeMetrics;
    private readonly IHistoryMetricsService _historyMetrics;
    private readonly IExperienceMetricsService _experienceMetrics;
    private readonly IGithubAuthService _githubService;

    public GitHubWebhookService(
        IChangeMetricsService changeMetrics,
        IHistoryMetricsService historyMetrics,
        IExperienceMetricsService experienceMetrics,
        IGithubAuthService githubService)
    {
        _changeMetrics = changeMetrics;
        _historyMetrics = historyMetrics;
        _experienceMetrics = experienceMetrics;
        _githubService = githubService;
    }

    public async Task<WebhookMetrics?> HandleEventAsync(string eventType, string payload)
{
    using var json = JsonDocument.Parse(payload);

    Console.WriteLine($" EVENT RECEIVED: {eventType}");

    if (eventType != "pull_request")
        return null;

    var pr = json.RootElement.GetProperty("pull_request");
    var number = pr.GetProperty("number").GetInt32();

    var repo = json.RootElement
        .GetProperty("repository")
        .GetProperty("name")
        .GetString();

    var owner = json.RootElement
        .GetProperty("repository")
        .GetProperty("owner")
        .GetProperty("login")
        .GetString();

    Console.WriteLine($"📌 PR detected: {owner}/{repo} #{number}");

    // ==========================
    // GET DATA
    // ==========================
    var changedFiles =
        await _githubService.GetChangedFilesAsync(owner!, repo!, number);

    var changeMetrics =
        _changeMetrics.Calculate(changedFiles);

    var historyMetrics =
        await _historyMetrics.Calculate(owner!, repo!, number);

    var experienceMetrics =
        await _experienceMetrics.CalculateExperienceMetrics(owner!, repo!, number);

    // ==========================
    // BUILD RESULT (IMPORTANT)
    // ==========================
    var result = new WebhookMetrics
    {
        ChangeMetrics = changeMetrics,
        HistoryMetrics = historyMetrics,
        ExperienceMetrics = experienceMetrics
    };

    // ==========================
    // DEBUG OUTPUT (FOR TESTING)
    // ==========================
    Console.WriteLine("===== WEBHOOK RESULT =====");
    Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions
    {
        WriteIndented = true
    }));

    return result;
}
}