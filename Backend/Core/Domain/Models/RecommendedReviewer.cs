namespace Core.Domain.Models;

public class RecommendedReviewer
{
    public string Name { get; set; }
    public double Score { get; set; }
    public List<string> Skills { get; set; }
}