using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using Share;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GitHubProfilingController : ControllerBase
{
    private readonly IProfilingService _profilingService;

    public GitHubProfilingController(IProfilingService profilingService)
    {
        _profilingService = profilingService;
    }

    [HttpGet("{userName}")]
    public async Task<ActionResult<GitHubProfileDto>> GetUserProfile(string userName, CancellationToken cancellationToken)
    {
        try
        {
            var userProfile = await _profilingService.GetUserProfileAsync(userName, cancellationToken);
            return Ok(userProfile);
        }
        catch (Exception ex)
        {
            // It's better to log the exception here
            return BadRequest(new { error = ex.Message });
        }
    }
}