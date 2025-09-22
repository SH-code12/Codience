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

           // var user = await _gitHubAuthService.SaveUserAsync(token.AccessToken, cancellationToken);
            return Ok(token);
        }
}
