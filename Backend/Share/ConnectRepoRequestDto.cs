namespace Share;

public class ConnectRepoRequestDto
{
    public string UserName { get; set; } = "";
    public string Owner { get; set; } = "";
    public string Repo { get; set; } = "";
}
