using Share;

namespace Core.Abstraction;

public interface IGitHubWebhookService
{
    Task<WebhookMetrics?> HandleEventAsync(string eventType, string payload);

}
