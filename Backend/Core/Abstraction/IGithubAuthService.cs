
using Share;

namespace Core.Abstraction;

public interface IGithubAuthService
{
    Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken = default);
    Task<AccessTokenResponse> PollForAccessTokenAsync(DeviceCodeResponse deviceCodeResponse, CancellationToken cancellationToken = default);
}
