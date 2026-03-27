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


    [HttpGet("repos/{userName}")]
    public async Task<ActionResult<IEnumerable<GitHubRepoDto>>> SaveRepositories(string userName)
    {
        try
        {
            var repos = await _gitHubAuthService.SaveRepositories(userName);

            if (repos == null || !repos.Any())
                return NotFound($"No repositories found for user: {userName}");

            return Ok(repos);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
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
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics/nf")]
    public async Task<ActionResult<int>> GetNF(string owner, string repo, int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);
        return Ok(files.Count());
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics/nd")]
    public async Task<ActionResult<int>> GetND(string owner, string repo, int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);

        var nd = files
            .Select(f => Path.GetDirectoryName(f.Filename))
            .Distinct()
            .Count();

        return Ok(nd);
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics/ns")]
    public async Task<ActionResult<int>> GetNS(string owner, string repo, int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);

        var ns = files
            .Select(f => f.Filename.Split('/')[0])
            .Distinct()
            .Count();

        return Ok(ns);

    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics/la")]
    public async Task<ActionResult<int>> GetLA(string owner, string repo, int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);
        var la = files.Sum(f => f.Additions);
        return Ok(la);
    }

    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics/ld")]
    public async Task<ActionResult<int>> GetLD(string owner, string repo, int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);
        var ld = files.Sum(f => f.Deletions);
        return Ok(ld);

    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/metrics/entropy")]
    public async Task<ActionResult<double>> GetEntropy(string owner, string repo, int pullNumber)
    {
        var files = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);

        var total = files.Sum(f => f.Additions + f.Deletions);

        if (total == 0) return Ok(0);

        var entropy = files.Sum(f =>
        {
            var changes = f.Additions + f.Deletions;
            if (changes == 0) return 0;

            var pi = (double)changes / total;
            return -pi * Math.Log2(pi);
        });

        return Ok(entropy);
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
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/history/ndev")]
    public async Task<ActionResult<int>> GetNDEV(string owner, string repo, int pullNumber)
    {
        var result = await _historyService.Calculate(owner, repo, pullNumber);
        return Ok(result.NDEV);
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/history/age")]
    public async Task<ActionResult<double>> GetAGE(string owner, string repo, int pullNumber)
    {
        var result = await _historyService.Calculate(owner, repo, pullNumber);
        return Ok(result.AGE);
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/history/nuc")]
    public async Task<ActionResult<int>> GetNUC(string owner, string repo, int pullNumber)
    {
        var result = await _historyService.Calculate(owner, repo, pullNumber);
        return Ok(result.NUC);

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
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/experience/exp")]
    public async Task<ActionResult<int>> GetEXP(string owner, string repo, int pullNumber)
    {
        var result =
            await _experienceService
            .CalculateExperienceMetrics(owner, repo, pullNumber);

        return Ok(result.EXP);
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/experience/rexp")]
    public async Task<ActionResult<int>> GetREXP(string owner,string repo,int pullNumber)
    {
        var result =
            await _experienceService
            .CalculateExperienceMetrics(owner, repo, pullNumber);

        return Ok(result.REXP);
    }
    [HttpGet("{owner}/{repo}/pulls/{pullNumber}/experience/sexp")]
    public async Task<ActionResult<int>> GetSEXP(string owner,string repo,int pullNumber)
    {
        var result =
            await _experienceService
            .CalculateExperienceMetrics(owner, repo, pullNumber);

        return Ok(result.SEXP);
    }
}

