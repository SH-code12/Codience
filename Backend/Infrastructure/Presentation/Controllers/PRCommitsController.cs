using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;

namespace Infrastructure.Presentation;

[ApiController]
[Route("api/[controller]")]
public class PRCommitsController : ControllerBase
{
    private readonly IPRCommitsService _service;
    private readonly IGithubAuthService _gitHubAuthService;

    public PRCommitsController(IPRCommitsService service, IGithubAuthService gitHubAuthService)
    {
        _service = service;
        _gitHubAuthService = gitHubAuthService;
    }

    [HttpGet("repos/{owner}/{repo}/pullrequests/{pullNumber}/commits/metrics")]
    public async Task<IActionResult> GetCommitsAnalytics(string owner,string repo,int pullNumber)
    {
        var result = await _service.CalculateAsync(owner, repo, pullNumber);
        return Ok(result);
    }
    [HttpGet("repos/{owner}/{repo}/pulls/{pullNumber}/commits")]
    public async Task<IActionResult> GetCommits(string owner, string repo, int pullNumber)
    {
        var result = await _gitHubAuthService.GetChangedFilesAsync(owner, repo, pullNumber);
        return Ok(result);
    }
}
