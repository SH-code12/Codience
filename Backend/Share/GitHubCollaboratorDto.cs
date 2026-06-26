
namespace share;


public class GitHubCollaboratorDto
{
    public string Login { get; set; }
    public long Id { get; set; }
    public string AvatarUrl { get; set; }
    public string HtmlUrl { get; set; }
    public string RoleName { get; set; }
    public PermissionsDto Permissions { get; set; }
}

public class PermissionsDto
{
    public bool Admin { get; set; }
    public bool Maintain { get; set; }
    public bool Push { get; set; }
    public bool Triage { get; set; }
    public bool Pull { get; set; }
}
