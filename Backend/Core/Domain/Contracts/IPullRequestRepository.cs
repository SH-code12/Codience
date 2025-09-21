using Core.Domain.Models;

namespace Core.Domain.Contracts;

public interface IPullRequestRepository : IGenericRepository<GitHubPullRequest, int>
{
      Task<IEnumerable<GitHubPullRequest>> GetByRepositoryIdAsync(int repositoryId);
}
