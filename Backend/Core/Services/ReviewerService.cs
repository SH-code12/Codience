using System.Net.Http.Json;
using Core.Abstraction;
using Core.Domain.Models;
using Polly;

namespace Core.Services;

public class ReviewerService : IReviewerService
{
    private readonly HttpClient _httpClient;

    public ReviewerService(IHttpClientFactory httpClient)
    {
        _httpClient = httpClient.CreateClient("ReviewerApiClient");
        
    }

    public async Task<ReviewerResponse> GetRecommendationsAsync(ReviewerRequest request)
    {
        var retryPolicy = Policy.Handle<HttpRequestException>()
            .OrResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
            .WaitAndRetryAsync(3, attempt => TimeSpan.FromSeconds(70));

        // This will combine with http://127.0.0.1:8000/ to make http://127.0.0.1:8000/api/recommend
        var response = await retryPolicy.ExecuteAsync(() => 
            _httpClient.PostAsJsonAsync("api/recommend", request));
        
        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            throw new Exception(error);
        }
        return await response.Content.ReadFromJsonAsync<ReviewerResponse>()?? new ReviewerResponse();
    }
}