using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using Share;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AnalyticsController : ControllerBase
{
    private readonly IAnalyticsService _analyticsService;

    public AnalyticsController(IAnalyticsService analyticsService)
    {
        _analyticsService = analyticsService;
    }

    [HttpGet("{userName}")]
    public async Task<ActionResult<UserAnalyticsDto>> GetUserAnalytics(
        string userName,
        [FromQuery] DateTime? startDate,
        [FromQuery] DateTime? endDate,
        [FromQuery] long? repositoryId,
        CancellationToken cancellationToken)
    {
        try
        {
            var analytics = await _analyticsService.GetUserAnalyticsAsync(userName, startDate, endDate, repositoryId, cancellationToken);
            return Ok(analytics);
        }
        catch (NotImplementedException)
        {
            return StatusCode(501, "The analytics feature is not yet implemented.");
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
}
