using Core.Abstraction;
using Microsoft.AspNetCore.Mvc;
using System.Text.Json;
using System.Net.Http.Headers;

[ApiController]
[Route("api/[controller]")]
public class JiraController : ControllerBase
{
    private readonly IJiraService _jiraService;

    public JiraController(IJiraService jiraService)
    {
        _jiraService = jiraService;
    }

    // Redirect to Jira login
    [HttpGet("login")]
    public IActionResult Login()
    {
        var clientId = "YOUR_CLIENT_ID";
        var redirectUri = "YOUR_CALLBACK_URL";
        var url = $"https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id={clientId}&scope=read:jira-user read:jira-work&redirect_uri={redirectUri}&response_type=code&prompt=consent";
        return Redirect(url);
    }

    // Callback after Jira OAuth
    [HttpGet("callback")]
    public async Task<IActionResult> Callback(string code)
    {
        var accessToken = await _jiraService.ExchangeCodeForAdminToken(code);

        var resources = await _jiraService.GetAccessibleResources(accessToken);
        Console.WriteLine("RESOURCES:");
        Console.WriteLine(resources.ToString());

        if (resources.ValueKind != JsonValueKind.Array || resources.GetArrayLength() == 0)
            return Ok(new { message = "No Jira sites found" });

        // Choose CloudId (replace YOUR-DOMAIN with actual Jira site)
        var cloud = resources.EnumerateArray()
            .FirstOrDefault(r => r.GetProperty("url").GetString()!.Contains("YOUR-DOMAIN"));

        if (cloud.ValueKind == JsonValueKind.Undefined)
            return Ok(new { message = "No Jira cloud found for the given domain" });

        var cloudId = cloud.GetProperty("id").GetString()!;
        Console.WriteLine($"Using CloudId: {cloudId}");

        
        var projects = await _jiraService.GetAllProjects(accessToken, cloudId);

        if (projects.ValueKind != JsonValueKind.Array || projects.GetArrayLength() == 0)
        {
            return Ok(new
            {
                message = "No projects found",
                debug = new
                {
                    cloudId,
                    note = "Check Admin permissions or Jira site"
                }
            });
        }

        
        var projectKey = projects[0].GetProperty("key").GetString()!;
        var issues = await _jiraService.GetIssues(accessToken, cloudId, projectKey);
        var roles = await _jiraService.GetProjectRoles(accessToken, cloudId, projectKey);

        return Ok(new
        {
            cloudId,
            Projects = projects,
            Issues = issues,
            Roles = roles
        });
    }

    [HttpGet("resources")]
    public async Task<IActionResult> Resources(string token)
    {
        var data = await _jiraService.GetAccessibleResources(token);
        return Ok(data);
    }
}