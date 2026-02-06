using Core.Abstraction;

using Microsoft.AspNetCore.Mvc;

namespace Infrastructure.Presentation.Controllers;


[ApiController]
[Route("api/[controller]")]
public class JiraController : ControllerBase
{
    private readonly IJiraService _jiraService;

    public JiraController(IJiraService jiraService) => _jiraService = jiraService;

    [HttpGet("callback")]
    public async Task<IActionResult> Callback(string code, Guid state) 
    {
        var token = await _jiraService.GetAccessTokenAsync(code);
        var accId = await _jiraService.GetJiraAccountIdAsync(token.AccessToken);
        await _jiraService.SaveJiraUserAsync(state, accId, token.AccessToken);
        return Ok(new { Message = "Jira Account Linked", JiraAccountId = accId });
    }
}

