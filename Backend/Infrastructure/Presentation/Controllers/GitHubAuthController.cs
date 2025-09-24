using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using Share;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubAuthController : ControllerBase
{
    private readonly IGithubAuthService _gitHubAuthService;

    public GitHubAuthController(IGithubAuthService gitHubAuthService)
    {
        _gitHubAuthService = gitHubAuthService;
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


}
