
using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;

namespace API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubAppController : ControllerBase
{
    private readonly IGitHubAppService _service;
    private readonly  IConfiguration _configuration;

    public GitHubAppController(IGitHubAppService service,IConfiguration configuration)
    {
        _service = service;
        _configuration=configuration;

    }

    [HttpGet("info")]
    public async Task<IActionResult> Info()
        => Ok(await _service.GetAuthenticatedAppAsync());

    [HttpGet("installations")]
    public async Task<IActionResult> Installations(
        int page = 1,
        int perPage = 30)
        => Ok(await _service.GetInstallationsAsync(page, perPage));

    [HttpGet("repo/{owner}/{repo}")]
    public async Task<IActionResult> Repo(string owner,string repo)
        => Ok(await _service.GetRepositoryInstallationAsync(owner, repo));

    [HttpGet("installed/{owner}/{repo}")]
    public async Task<IActionResult> Installed(string owner,string repo)
        => Ok(await _service.IsInstalledAsync(owner, repo));

    
    [HttpGet("connect")]
    public async Task<IActionResult> Connect(string userName,string owner,string repo)
        => Ok(await _service.ConnectRepositoryAsync(userName,owner,repo));

    [HttpPost("token/{installationId}")]
    public async Task<IActionResult> Token(long installationId)
        => Ok(await _service.CreateInstallationTokenAsync(
            installationId));

    
    


    [HttpGet("callback")]
    public IActionResult Callback(long? installation_id,string? setup_action,string? state)
    {
        var frontend = _configuration["Frontend:Url"];

        return Redirect(
            $"{frontend}/github/callback" +
            $"?installationId={installation_id}" +
            $"&setupAction={setup_action}" +
            $"&state={state}");
    }

    [HttpDelete("installation/{installationId}")]
    public async Task<IActionResult> Delete(long installationId)
    {
        await _service.DeleteInstallationAsync(installationId);

        return Ok(new
        {
            Message = "Installation deleted"
        });
    }
}