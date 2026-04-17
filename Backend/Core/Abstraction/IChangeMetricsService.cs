using Share;

namespace Core.Abstraction;

public interface IChangeMetricsService
{
        ChangeMetricsDto Calculate(IEnumerable<GitHubFileDto> files);

}
