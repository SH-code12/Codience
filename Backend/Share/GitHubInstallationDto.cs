namespace Share;

public class GitHubInstallationDto
{
    public long Id { get; set; }
    public string App_Slug { get; set; } = "";
    public string Target_Type { get; set; } = "";

    public GitHubAccountDto Account { get; set; } = new();
}
