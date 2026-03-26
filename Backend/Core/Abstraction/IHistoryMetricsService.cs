using Share;

namespace Core.Abstraction;

public interface IHistoryMetricsService
{
 Task<HistoryMetricsDto> Calculate(string owner,string repo,int pullNumber);
 
}
