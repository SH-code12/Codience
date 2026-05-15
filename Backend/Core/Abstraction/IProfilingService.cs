using Share;

namespace Core.Abstraction;

public interface IProfilingService
{
    Task<GitHubProfileDto> GetUserProfileAsync(string userName, CancellationToken cancellationToken = default);
}