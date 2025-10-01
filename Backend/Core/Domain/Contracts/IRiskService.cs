using Core.Domain.Models;

namespace Core.Domain.Contracts;

public interface IRiskService
{
    Task<RiskResult> GetPredictionAsync(RiskInput input); 
}