using System.Text.Json.Serialization;

namespace Core.Domain.Models;

public class DeviceCodeResponse
{
       [JsonPropertyName("device_code")]
        public string DeviceCode { get; set; } = default!;

        [JsonPropertyName("user_code")]
        public string UserCode { get; set; } = default!;

        [JsonPropertyName("verification_uri")]
        public string VerificationUri { get; set; } = default!;

        [JsonPropertyName("expires_in")]
        public int ExpiresIn { get; set; }

        [JsonPropertyName("interval")]
        public int Interval { get; set; }
}
