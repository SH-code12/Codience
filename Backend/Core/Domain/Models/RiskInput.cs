namespace Core.Domain.Models;

public class RiskInput
{
    public string Repo { get; set; } = string.Empty;
    public string ProblemStatement { get; set; } = string.Empty;
    public string Patch { get; set; } = string.Empty;
}