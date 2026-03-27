public class GitHubCommitDto
{
    public string Sha { get; set; }

    public GitHubCommit Commit { get; set; }

    public GitHubUser Author { get; set; }

    // helper properties عشان HistoryMetricsService
    public string AuthorLogin =>
        Author?.Login ?? "";

    public DateTime CommitDate =>
        Commit?.Author?.Date ?? DateTime.MinValue;
}

public class GitHubCommit
{
    public GitHubCommitAuthor Author { get; set; }
}

public class GitHubCommitAuthor
{
    public DateTime Date { get; set; }
}

public class GitHubUser
{
    public string Login { get; set; }
}