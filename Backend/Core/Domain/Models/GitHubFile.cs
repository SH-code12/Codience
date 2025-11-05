namespace Core.Domain.Models;

public class GitHubFile:BaseEntity<int>
{

    public string Filename { get; set; }
    public string Status { get; set; }
    public int Additions { get; set; }
    public int Deletions { get; set; }
    public int Changes { get; set; }
    public string BlobUrl { get; set; }
    public string RawUrl { get; set; }
}
