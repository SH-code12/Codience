namespace Core.Domain.Models;

public class RiskResult
{
    public string risk_level { get; set; } = string.Empty;
    public double risk_score { get; set; }
}