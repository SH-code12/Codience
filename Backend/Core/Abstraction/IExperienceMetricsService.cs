using Share;

namespace Core.Abstraction;

public interface IExperienceMetricsService
{
    Task<ExperienceMetricsDto> CalculateExperienceMetrics(string owner, string repo, int pullRequestNumber);
}
