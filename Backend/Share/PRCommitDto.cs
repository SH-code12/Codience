namespace Share;

public class PRCommitDto
{
    public string CommitSha { get; set; }

    public string Author { get; set; }

    public DateTime Date { get; set; }
    public ExperienceMetricsDto Experience { get; set; }
    public HistoryMetricsDto History { get; set; }
    public ChangeMetricsDto Change { get; set; }
}
