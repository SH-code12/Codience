
using Share;

namespace Core.Abstraction;

public interface IGithubAuthService
{
    Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken = default);
    Task<AccessTokenResponse> PollForAccessTokenAsync(DeviceCodeResponse deviceCodeResponse, CancellationToken cancellationToken = default);
    Task<AuthUserDto> SaveUserAsync(string accessToken, CancellationToken ct = default);
    Task<IEnumerable<GitHubRepoDto>> SaveRepositories(string UserName);
    Task<IEnumerable<GitHubPullRequestDto>> GetPullRequestsAsync(string userName, string repoName);

    Task<GitHubPullRequestDto> GetPullRequest(string owner, int pullNumber, string repo);   
    Task<IEnumerable<GitHubFileDto>> GetChangedFilesAsync(string owner, string repo, int pullNumber);
    Task<IEnumerable<GitHubCommitDto>>GetCommitsByPath(string owner, string repo, string filePath);
    Task<IEnumerable<GitHubCommitDto>> GetAllCommits(string owner, string repo,string author);
Task<IEnumerable<GitHubCommitDto>> GetPullRequestCommits(string owner, string repo, int pullNumber);
}
