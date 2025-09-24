namespace Share;
public class GitHubPullRequestDto
{
    public GitHubPullRequestDto(long number, string title, string htmlUrl, string state, DateTime createdAt, string name)
    {
        Number = number;
        Title = title;
        HtmlUrl = htmlUrl;
        State = state;
        CreatedAt = createdAt;
        Name = name;
    }

    public long  Number { get; }
    public string Title { get; }
    public string? HtmlUrl { get; }
    public string State { get; }
    public DateTime CreatedAt { get; }
    public string Name { get; }

}