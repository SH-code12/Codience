
using Share;

namespace Core.Abstraction;

public interface IGithubAuthService
{
    Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken = default);
    Task<AccessTokenResponse> PollForAccessTokenAsync(DeviceCodeResponse deviceCodeResponse, CancellationToken cancellationToken = default);
    Task<AuthUserDto> SaveUserAsync(string accessToken, CancellationToken ct = default);
    Task<IEnumerable<GitHubRepoDto>> SaveRepositories(string UserName);
    Task<IEnumerable<GitHubPullRequestDto>> GetPullRequestsAsync(string userName, string repoName);

}
