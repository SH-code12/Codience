namespace Share;
public class CommitChangesDto

{
    public string CommitSha { get; set; }
    public int TotalFiles { get; set; }
    public int TotalAdditions { get; set; }
    public int TotalDeletions { get; set; }

    public IEnumerable<CommitFileChangeDto> Files { get; set; }
}

public class CommitFileChangeDto
{
    public string FileName { get; set; }
    public int Additions { get; set; }
    public int Deletions { get; set; }
}