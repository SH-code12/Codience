namespace Core.Domain.Models;

public class ReviewerResponse
{
    public List<RecommendedReviewer> Reviewers { get; set; } = new();
}