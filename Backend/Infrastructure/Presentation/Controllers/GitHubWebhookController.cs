using System.Text.Json;
using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubWebhookController : ControllerBase
{
  private readonly IGitHubWebhookService _webhookService;

    public GitHubWebhookController(IGitHubWebhookService webhookService)
    {
        _webhookService = webhookService;
    }

    [HttpPost("github")]
public async Task<IActionResult> ReceiveWebhook(
    [FromHeader(Name = "X-GitHub-Event")] string eventType,
    [FromBody] JsonElement payload)
{
    try
    {
        var result = await _webhookService.HandleEventAsync(
            eventType,
            payload.GetRawText()
        );

        return Ok(result);
    }
    catch (Exception ex)
    {
        Console.WriteLine(ex.ToString());
        return StatusCode(500, ex.Message);
    }
}
       
}
