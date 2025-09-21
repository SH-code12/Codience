namespace Share;

public record AuthUserDto
{
    public string GitHubId { get; init; } = default!;
    public string UserName { get; init; } = default!;
    public string Email { get; init; } = default!;
    public string AccessToken { get; init; } = default!;
}

