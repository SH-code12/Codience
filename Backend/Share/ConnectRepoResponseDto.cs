namespace Share;

public class ConnectRepoResponseDto
{

    public bool IsInstalled { get; set; }
    public bool IsAdmin { get; set; }
    public string Message { get; set; } = "";
    public string? InstallUrl { get; set; }
}

