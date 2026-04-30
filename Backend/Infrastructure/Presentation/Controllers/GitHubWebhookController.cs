using Microsoft.AspNetCore.Mvc;
using System.Text.Json;
using Core.Abstraction;
using Share;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubWebhookController : ControllerBase
{
    private readonly IGitHubWebhookService _service;

    public GitHubWebhookController(
        IGitHubWebhookService service)
    {
        _service = service;
    }

    
    [HttpPost("github")]
    public async Task<IActionResult> Receive(
        [FromHeader(Name = "X-GitHub-Event")] string eventType,
        [FromBody] JsonElement payload)
    {
        try
        {
            var result = await _service.HandleEventAsync(
                eventType,
                payload.GetRawText());

            return Ok(result);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new
            {
                message = ex.Message
            });
        }
    }
    
 
    [HttpGet("installation-id/{owner}/{repo}")]
    public async Task<IActionResult> InstallationId(
        string owner,
        string repo)
    {
        try
        {
            var result =
                await _service.GetInstallationIdAsync(owner, repo);

            return Ok(new
            {
                installationId = result
            });
        }
        catch (Exception ex)
        {
            return BadRequest(new
            {
                message = ex.Message
            });
        }
    }

    
    [HttpDelete("{owner}/{repo}")]
    public async Task<IActionResult> Disconnect(
        string owner,
        string repo)
    {
        try
        {
            await _service.DisconnectRepositoryAsync(
                owner,
                repo);

            return Ok(new
            {
                message = "Disconnected successfully"
            });
        }
        catch (Exception ex)
        {
            return BadRequest(new
            {
                message = ex.Message
            });
        }
    }
}