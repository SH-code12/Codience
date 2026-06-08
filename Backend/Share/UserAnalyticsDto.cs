namespace Share;

public class UserAnalyticsDto
{
    public int AssignedPullRequestsCount { get; set; }
    public int ReviewedPullRequestsCount { get; set; }
    public int CreatedPullRequestsCount { get; set; }
    public double AverageResponseTime { get; set; }
    public int AiRecommendationCount { get; set; }
}
