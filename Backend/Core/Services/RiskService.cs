using Core.Domain.Contracts;
using System.Net.Http.Json;
using Core.Domain;
using Core.Domain.Models;
using Polly;

namespace Core.Services;

public class RiskService : IRiskService
{
    private readonly HttpClient httpClient;
    

    public RiskService(IHttpClientFactory httpClientFactory)
    {
        httpClient = httpClientFactory.CreateClient("FastApiClient");
    }
    public async Task<RiskResult> GetPredictionAsync(RiskInput input)
    {
        var retryPolicy = Policy
            .Handle<HttpRequestException>()
            .OrResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
            .WaitAndRetryAsync(3, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)));

        var payload = new
        {
            repo = input.Repo,
            problem_statement = input.ProblemStatement,
            patch = input.Patch
        };

        var response = await retryPolicy.ExecuteAsync(() =>
            httpClient.PostAsJsonAsync("/predict", payload));

        if (!response.IsSuccessStatusCode)
        {
            var errorContent = await response.Content.ReadAsStringAsync();
            throw new Exception($"Prediction failed: {response.StatusCode} - {errorContent}");
        }

        var result = await response.Content.ReadFromJsonAsync<RiskResult>();
        RiskResult riskResult = new RiskResult
        {
            Prediction = result!.Prediction.ToString(),
            Score = (double)result.Score
        };
        return riskResult;
    }
    

}