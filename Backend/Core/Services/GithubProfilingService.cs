using System.Net.Http.Headers;
using System.Net.Http.Json;
using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Share;

namespace Core.Services; 

public class GithubProfilingService : IProfilingService
{
    private readonly IUnitOfWork _unitOfWork;
    private readonly HttpClient _httpClient; 

    public GithubProfilingService(IUnitOfWork unitOfWork, HttpClient httpClient)
    {
        _unitOfWork = unitOfWork;
        _httpClient = httpClient;
    }

    public async Task<GitHubProfileDto> GetUserProfileAsync(string userName, CancellationToken cancellationToken = default)
    {
        var userRepo = _unitOfWork.GetGenericRepository<AuthUser, Guid>();
        var authUser = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == userName);

        if (authUser is null)
        {
            throw new Exception("User not found");
        }
        
        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", authUser.AccessToken);
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");

        var response = await _httpClient.GetAsync($"https://api.github.com/users/{userName}", cancellationToken);
        response.EnsureSuccessStatusCode();

        var profile = await response.Content.ReadFromJsonAsync<GitHubProfileDto>(cancellationToken: cancellationToken);

        if (profile is null)
        {
            throw new Exception("Failed to deserialize user profile from GitHub API.");
        }

        return profile;
    }
}