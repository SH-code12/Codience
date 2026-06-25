namespace Core.Domain.Models;

public class UserConnection : BaseEntity<int>
{
    public Guid UserId { get; set; }

    public string ConnectionId { get; set; } = string.Empty;

    public string Owner { get; set; } = string.Empty;

    public string RepoName { get; set; } = string.Empty;

    // Navigation Property
    public AuthUser User { get; set; } = null!;
}