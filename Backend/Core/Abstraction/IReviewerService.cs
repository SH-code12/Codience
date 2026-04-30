using Core.Domain.Models;

namespace Core.Abstraction;

public interface IReviewerService
{
    Task<ReviewerResponse> GetRecommendationsAsync(ReviewerRequest request);
}