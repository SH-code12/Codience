namespace Share;

public class HistoryMetricsDto
{
    public int NDEV { get; set; }   //The number of developers who have made at least one change to the file.
    public double AGE { get; set; } // in days `The age of the file in days, calculated as the difference between the current date and the date of the first commit that modified the file.
    public int NUC { get; set; }   //The number of unique commits that have modified the file.
}

