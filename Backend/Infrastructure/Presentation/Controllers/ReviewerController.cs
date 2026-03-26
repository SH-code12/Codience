using Core.Abstraction;
using Core.Domain.Models;
using Microsoft.AspNetCore.Mvc;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ReviewerController : ControllerBase
{
    private readonly IReviewerService _reviewerService;

    public ReviewerController(IReviewerService reviewerService)
    {
        _reviewerService = reviewerService;
    }

    [HttpPost("recommend")]
    public async Task<IActionResult> RecommendReviewers([FromBody] ReviewerRequest request)
    {
        // Validate the specific fields required by the FastAPI Engine
        if (string.IsNullOrWhiteSpace(request.Owner) || 
            string.IsNullOrWhiteSpace(request.Repo) || 
            request.PrNumber <= 0)
        {
            return BadRequest("Owner, Repo, and a valid PR Number are required to generate recommendations.");
        }

        try
        {
            var res = await _reviewerService.GetRecommendationsAsync(request);
            return Ok(res);
        }
        catch (HttpRequestException ex)
        {
            return StatusCode(503, new { error = "AI recommendation service is currently unavailable", details = ex.Message });
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { error = ex.Message });
        }
    }
}