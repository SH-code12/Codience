using Share;

namespace Core.Abstraction;

public interface IGitHubWebhookService
{
     Task<(GitHubPullRequestDto response, WebhookMetrics metrics)?> HandleEventAsync(string eventType, string payload);

     Task<WebhookResponseDto> HandleWebhookAsync(string eventType, string payload);
    // Get installation id   
      Task<long?> GetInstallationIdAsync(string owner, string repo);   
     // Disconnect repository  
      Task DisconnectRepositoryAsync(string owner, string repo);
      }

