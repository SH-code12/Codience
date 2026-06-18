using Core.Abstraction;
using Share;

namespace Core.Services;

public class AnalyticsService : IAnalyticsService
{
    private readonly IGitHubAppService _githubAppService;

    public AnalyticsService(IGitHubAppService githubAppService)
    {
        _githubAppService = githubAppService;
    }

    public async Task<UserAnalyticsDto> GetUserAnalyticsAsync(string userName, DateTime? startDate, DateTime? endDate, long? repositoryId, CancellationToken cancellationToken = default)
    {
        // Fetch data from GitHub API
        var pullRequests = await _githubAppService.GetPullRequestsAsync(repositoryId);

        var assignedPrs = pullRequests.Count(pr => pr.Assignees.Any(a => a.Login == userName));
        var reviewedPrs = pullRequests.Count(pr => pr.User.Login != userName && pr.requested_reviewers.Any(r => r.Login == userName));
        var createdPrs = pullRequests.Count(pr => pr.User.Login == userName);

        //TODO: implement avg response time
        return new UserAnalyticsDto
        {
            AssignedPullRequestsCount = assignedPrs,
            ReviewedPullRequestsCount = reviewedPrs,
            CreatedPullRequestsCount = createdPrs,
            AiRecommendationCount = 0 // Recommendations are not available from GitHub API directly
        };
    }
}
