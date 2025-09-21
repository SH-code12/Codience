using Core.Domain.Models;

namespace Core.Domain.Contracts;

public interface IRepositoryForRepositories : IGenericRepository<GitHubRepo, int>

{
     Task<GitHubRepo?> GetByNameAsync(string name);
}

