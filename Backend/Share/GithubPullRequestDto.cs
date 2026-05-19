namespace Share;
public class GitHubPullRequestDto
{
    public GitHubPullRequestDto(long number, string title, string state, DateTime createdAt, string name)
    {
        Number = number;
        Title = title;
        State = state;
        CreatedAt = createdAt;
        Name = name;
    }

    public long  Number { get; }
    public string Title { get; }

    public string State { get; }
    public DateTime CreatedAt { get; }
    public string Name { get; }
    public GitHubUserDto User {get;set;}
    public List<GitHubUserDto> Assignees { get; set; } = new();
    public List<GitHubUserDto> requested_reviewers { get; set; } = new();
}

public class GitHubUserDto
{
    public string Login {get;set;}
}

