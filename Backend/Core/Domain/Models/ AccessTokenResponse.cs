using System.Text.Json.Serialization;

namespace Core.Domain.Models;

public class AccessTokenResponse
{
      [JsonPropertyName("access_token")]
        public string AccessToken { get; set; } = default!;

        [JsonPropertyName("token_type")]
        public string TokenType { get; set; } = default!;

        [JsonPropertyName("scope")]
        public string Scope { get; set; } = default!;

        [JsonPropertyName("error")]
        public string? Error { get; set; }
    }
