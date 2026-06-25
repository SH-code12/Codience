using Share;
namespace Core.Abstraction;

public interface IRealTimeNotification
{
    
  Task NotifyPullRequestCreatedAsync( GitHubPullRequestDto dto);

}
