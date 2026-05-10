using Microsoft.Extensions.Configuration;
using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;
using System.Net.Http.Headers;
using Infrastructure.Presentation.DTOs;
using Share;

[ApiController]
[Route("api/[controller]")]
public class JiraController : ControllerBase
{
    private readonly IJiraService _jiraService;
    private readonly IConfiguration _configuration;

    public JiraController(IJiraService jiraService, IConfiguration configuration)
    {
        _jiraService = jiraService;
        _configuration = configuration;
    }

    [HttpGet("login")]
    public IActionResult Login()
    {
        var clientId = _configuration["Jira:ClientId"];
        var redirectUri = _configuration["Jira:CallbackUrl"];
        var url = "https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=" + clientId + "&scope=read:jira-user read:jira-work&redirect_uri=" + redirectUri + "&response_type=code&prompt=consent";
        return Redirect(url);
    }

    [HttpGet("callback")]
    public async Task<IActionResult> Callback(string code)
    {
        var accessToken = await _jiraService.ExchangeCodeForAdminToken(code);
        var resources = await _jiraService.GetAccessibleResources(accessToken);

        if (resources.ValueKind != JsonValueKind.Array || resources.GetArrayLength() == 0)
            return Ok(new { accessToken, message = "No Jira sites found" });

        var cloud = resources.EnumerateArray()
            .FirstOrDefault(r => r.GetProperty("url").GetString()!.Contains(_configuration["Jira:Domain"]));

        if (cloud.ValueKind == JsonValueKind.Undefined)
            return Ok(new { accessToken, message = "No Jira cloud found" });

        var cloudId = cloud.GetProperty("id").GetString()!;
        var projects = await _jiraService.GetAllProjects(accessToken, cloudId);

        return Ok(new
        {
            accessToken,
            cloudId,
            Projects = projects
        });
    }

    [HttpPost("assigned-tickets")]
    public async Task<IActionResult> GetAssignedTickets([FromBody] JiraRequestDto request)
    {
        try
        {
            var issues = await _jiraService.GetAssignedIssuesAsync(request.Token, request.CloudId, request.ProjectKey,
                request.AssigneeName);
            return Ok(issues);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    [HttpPost("assign-issue")]
    public async Task<IActionResult> AssignIssue([FromBody] JiraAssignIssueDto request)
    {
        try
        {
            var success = await _jiraService.AssignIssueAsync(request.Token, request.CloudId, request.IssueKey, request.AccountId);
            if (success) return Ok(new { message = "Issue assigned successfully" });
            return BadRequest(new { message = "Failed to assign issue" });
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    [HttpGet("me")]
    public async Task<IActionResult> GetCurrentUser(string token)
    {
        try
        {
            var user = await _jiraService.GetCurrentUserAsync(token);
            return Ok(user);
        }
        catch (Exception ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
}