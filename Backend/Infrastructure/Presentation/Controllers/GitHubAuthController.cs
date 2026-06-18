using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using Share;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubAuthController : ControllerBase
{
    private readonly IGithubAuthService _gitHubAuthService;
    private readonly IChangeMetricsService _metricsService;
    private readonly IHistoryMetricsService _historyService;
    private readonly IExperienceMetricsService _experienceService;
    public GitHubAuthController(IGithubAuthService gitHubAuthService, IChangeMetricsService metricsService, IHistoryMetricsService historyService, IExperienceMetricsService experienceService)
    {
        _gitHubAuthService = gitHubAuthService;
        _metricsService = metricsService;
        _historyService = historyService;
        _experienceService = experienceService;
    }

    [HttpGet("login")]
    public IActionResult Login()
    {
        var url = _gitHubAuthService.GetGitHubAuthorizationUrl();
        return Redirect(url);
    }

    [HttpGet("callback")]
    public async Task<IActionResult> Callback(string code, CancellationToken cancellationToken)
    {
        var token = await _gitHubAuthService.ExchangeCodeForAccessTokenAsync(code, cancellationToken);
        if (string.IsNullOrEmpty(token.AccessToken))
        {
            return BadRequest(new { error = token.Error ?? "Failed to get access token." });
        }

        var user = await _gitHubAuthService.SaveUserAsync(token.AccessToken, cancellationToken);
        return Ok(user);
    }

    [HttpGet("device-code")]
    public async Task<IActionResult> GetDeviceCode(CancellationToken cancellationToken)
    {
        var code = await _gitHubAuthService.GetDeviceCodeAsync(cancellationToken);
        return Ok(code);
    }

    [HttpPost("token")]
    public async Task<IActionResult> GetAccessToken([FromBody] DeviceCodeResponse deviceCode, CancellationToken cancellationToken)
    {
        var token = await _gitHubAuthService.PollForAccessTokenAsync(deviceCode, cancellationToken);
        if (string.IsNullOrEmpty(token.AccessToken))
        {
            return BadRequest(new { error = token.Error ?? "Access token not received yet" });
        }

        var user = await _gitHubAuthService.SaveUserAsync(token.AccessToken, cancellationToken);

        return Ok(user);
    }

    [HttpGet("{userName}/{repoName}/pulls")]
    public async Task<ActionResult<IEnumerable<GitHubPullRequestDto>>> GetPullRequests(
           string userName,
           string repoName,
           CancellationToken ct)
    {
        try
        {
            var pulls = await _gitHubAuthService.GetPullRequestsAsync(userName, repoName);
            return Ok(pulls);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}")]
    public async Task<ActionResult<GitHubPullRequestDto>> GetPullRequest(
    string owner,
    string repo,
    int pullNumber)
    {
        var pullRequest = await _gitHubAuthService.GetPullRequest(
            owner,
            pullNumber,
            repo);

        return Ok(pullRequest);
    }

    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/files")]
    public async Task<ActionResult<IEnumerable<GitHubFileDto>>> GetChangedFiles(
        string owner,
        string repo,
        int pullNumber,
        CancellationToken ct)
    {
        try
        {
            var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);
            return Ok(files);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics")]
    public async Task<ActionResult<ChangeMetricsDto>> GetAllMetrics(
            string owner,
            string repo,
            int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);

        if (files == null || !files.Any())
            return NotFound("No files found for this PR");

        var metrics = _metricsService.Calculate(files);

        return Ok(metrics);
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/history")]

    public async Task<ActionResult<HistoryMetricsDto>> GetHistoryMetrics(
    string owner,
    string repo,
    int pullNumber)
    {
        var result = await _historyService.Calculate(owner, repo, pullNumber);
        return Ok(result);
    }

    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/experience")]
    public async Task<ActionResult<ExperienceMetricsDto>>
GetExperienceMetrics(string owner, string repo, int pullNumber)
    {
        var result =
            await _experienceService
            .CalculateExperienceMetrics(owner, repo, pullNumber);

        return Ok(result);
    }


    [HttpGet("repos")]
    public async Task<IActionResult> GetRepos(string userName, int page = 1, int pageSize = 30)
    {
        var result =
            await _gitHubAuthService
            .GetRepositoriesAsync(userName, page, pageSize);

        return Ok(result);
    }
}

