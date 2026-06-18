// ===============================
// File: Core.Abstraction/IGitHubAppService.cs
// ===============================
using Share;

namespace Core.Abstraction;

public interface IGitHubAppService
{
    Task<GitHubAppDto> GetAuthenticatedAppAsync();

    Task<IReadOnlyList<GitHubInstallationDto>> GetInstallationsAsync(int page = 1,int perPage = 30);

    Task<GitHubInstallationDto?> GetRepositoryInstallationAsync(string owner,string repo);

    Task<bool> IsInstalledAsync(string owner,string repo);

    Task<string> CreateInstallationTokenAsync(long installationId);

    Task<string> GetInstallUrlAsync(string owner);
    Task<bool> IsUserAdminAsync(string userName, string owner, string repo);

    Task<ConnectRepoResponseDto> ConnectRepositoryAsync(string userName, string owner, string repo);
    Task DeleteInstallationAsync(long installationId);
    Task<IReadOnlyList<GitHubPullRequestDto>> GetPullRequestsAsync(long? repositoryId);
}