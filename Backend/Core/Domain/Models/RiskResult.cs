namespace Core.Domain.Models;

public class RiskResult
{
    public string Prediction { get; set; } = string.Empty;
    public double Score { get; set; }
}