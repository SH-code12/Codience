namespace Share;

public class ChangeMetricsDto
{
    public int NFiles { get; set; }
    public int NDirectories { get; set; }
    public int NSubsystems { get; set; }
    public int LinesAdded { get; set; }
    public int LinesDeleted { get; set; }
    public double Entropy { get; set; }
}
