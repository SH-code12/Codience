using Share;

namespace Core.Abstraction;

public interface IAnalyticsService
{
    Task<UserAnalyticsDto> GetUserAnalyticsAsync(string userName, DateTime? startDate, DateTime? endDate, long? repositoryId, CancellationToken cancellationToken = default);
}
