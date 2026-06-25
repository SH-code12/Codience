using System.Text.Json.Serialization;

namespace Share;
public class GitHubPullRequestDto
{
    public GitHubPullRequestDto(long number, string title, string state, DateTime createdAt, string repositoryName,string owner)
    {
        Number = number;
        Title = title;
        State = state;
        CreatedAt = createdAt;
        RepositoryName = repositoryName;
        Owner = owner;
    }

    public long Number { get; set; }

    [JsonPropertyName("title")]
    public string Title { get; set; }

    [JsonPropertyName("body")]
    public string Description { get; set; }

    [JsonPropertyName("diff_url")]
    public string DiffUrl { get; set; }

    public string  DiffContent { get; set; }    

    [JsonPropertyName("state")]
    public string State { get; set; }

    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }

    public string RepositoryName { get; set; }
    public GitHubUserDto User {get;set;}
    public  string Owner  { get; set; } 
    public List<GitHubUserDto> Assignees { get; set; } = new();
    public List<GitHubUserDto> requested_reviewers { get; set; } = new();
}

public class GitHubUserDto
{
    public string Login {get;set;}
}

