using Share;

namespace Core.Abstraction;

public interface IMetricsService
{
        ChangeMetricsDto Calculate(IEnumerable<GitHubFileDto> files);

}
