using System.Net.Http.Headers;
using Core.Abstraction;
using Microsoft.Extensions.Configuration;

using Share;
using System.Net.Http.Json;
using Core.Domain.Models;
using Core.Domain.Contracts;

public class GitHubAuthService : IGithubAuthService
{
    private readonly HttpClient _httpClient;
    private readonly string clientId;
    private readonly string clientSecret;
    private readonly IUnitOfWork _authUow;

    public GitHubAuthService(HttpClient httpClient, IConfiguration configuration, IUnitOfWork authUow)
    {
        _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        clientId = configuration["GitHub:ClientId"]!;
        clientSecret = configuration["GitHub:ClientSecret"]!;
        _authUow = authUow;

    }


    public async Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken = default)
    {


        var req = new HttpRequestMessage(HttpMethod.Post, "https://github.com/login/device/code")
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
                {
                    { "client_id", clientId },
                    { "scope", "repo read:user user:email"}
                })
        };
        req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

        var res = await _httpClient.SendAsync(req, cancellationToken);
        res.EnsureSuccessStatusCode();

        var deviceCode = await res.Content.ReadFromJsonAsync<DeviceCodeResponse>(cancellationToken: cancellationToken);
        return deviceCode ?? throw new Exception("Device code response is null");
    }

    public async Task<AccessTokenResponse> PollForAccessTokenAsync(DeviceCodeResponse deviceCodeResponse, CancellationToken cancellationToken = default)
    {


        var interval = deviceCodeResponse.Interval;
        var expiry = DateTime.UtcNow.AddSeconds(deviceCodeResponse.ExpiresIn);

        while (DateTime.UtcNow < expiry)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var req = new HttpRequestMessage(HttpMethod.Post, "https://github.com/login/oauth/access_token")
            {
                Content = new FormUrlEncodedContent(new Dictionary<string, string>
                    {
                        { "client_id", clientId },
                        { "client_secret", clientSecret },
                        { "device_code", deviceCodeResponse.DeviceCode },
                        { "grant_type", "urn:ietf:params:oauth:grant-type:device_code" }
                    })
            };
            req.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

            var res = await _httpClient.SendAsync(req, cancellationToken);
            var json = await res.Content.ReadFromJsonAsync<AccessTokenResponse>(cancellationToken: cancellationToken);

            if (json == null) throw new Exception("Failed to parse access token response");

            if (!string.IsNullOrEmpty(json.AccessToken))
                return json;

            if (json.Error == "authorization_pending")
            {
                await Task.Delay(TimeSpan.FromSeconds(interval), cancellationToken);
                continue;
            }

            if (json.Error == "slow_down")
            {
                interval += 5;
                await Task.Delay(TimeSpan.FromSeconds(interval), cancellationToken);
                continue;
            }

            // أي Error تاني: access_denied, expired_token ...
            return json;
        }

        throw new TimeoutException("Device code expired before authorization.");
    }



    public async Task<AuthUserDto> SaveUserAsync(string accessToken, CancellationToken ct = default)
    {
        if (string.IsNullOrEmpty(accessToken))
            throw new ArgumentException("Access token cannot be null or empty.");


        if (_httpClient == null)
            throw new InvalidOperationException("_httpClient is not initialized.");
        if (_authUow == null)
            throw new InvalidOperationException("_authUow is not initialized.");

        var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();
        if (userRepo == null)
            throw new InvalidOperationException("userRepo is null. Check GetGenericRepository implementation.");


        _httpClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");


        var response = await _httpClient.GetAsync("https://api.github.com/user", ct);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync(ct);
            throw new Exception($"GitHub API error: {response.StatusCode} - {errorBody}");
        }

        var userDto = await response.Content.ReadFromJsonAsync<AuthUserDto>(cancellationToken: ct);
        if (userDto == null)
            throw new Exception("GitHub user API returned null.");

        var gitHubIdString = userDto.GitHubId.ToString();
        if (string.IsNullOrEmpty(gitHubIdString))
            throw new Exception("GitHubId is null or empty.");


        var existingUser = await userRepo.FirstOrDefaultAsync(u => u.GitHubId == gitHubIdString);
        if (existingUser != null)
        {
            existingUser.AuthUserName = userDto.UserName ?? existingUser.AuthUserName;
            existingUser.Email = userDto.Email ?? existingUser.Email;
            existingUser.AccessToken = accessToken;

            await _authUow.SaveChangesAsync();

            return new AuthUserDto
            {
                GitHubId = userDto.GitHubId,
                UserName = existingUser.AuthUserName,
                Email = existingUser.Email,
                AccessToken = existingUser.AccessToken
            };
        }


        var newUser = new AuthUser
        {
            Id = Guid.NewGuid(),
            GitHubId = gitHubIdString,
            AuthUserName = userDto.UserName ?? "Unknown",
            Email = userDto.Email ?? string.Empty,
            AccessToken = accessToken
        };

        await userRepo.AddAsync(newUser);
        await _authUow.SaveChangesAsync();

        return new AuthUserDto
        {
            GitHubId = userDto.GitHubId,
            UserName = newUser.AuthUserName,
            Email = newUser.Email,
            AccessToken = newUser.AccessToken
        };
    }



    public async Task<IEnumerable<GitHubRepoDto>> SaveRepositories(string userName)
    {
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");

        var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();
        var authUser = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == userName);



        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", authUser!.AccessToken);


        var response = await _httpClient.GetAsync("https://api.github.com/user/repos?visibility=all");
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            throw new Exception($"GitHub API error: {response.StatusCode} - {errorBody}");
        }

        var reposJson = await response.Content.ReadFromJsonAsync<List<GitHubRepo>>(cancellationToken: CancellationToken.None);
        if (reposJson == null)
            throw new Exception("GitHub returned null repos list.");

        var repoRepo = _authUow.GetGenericRepository<GitHubRepo, int>();

        foreach (var repo in reposJson)
        {
            var existingRepo = await repoRepo.FirstOrDefaultAsync(r => r.Name == repo.Name && r.UserId == authUser.Id);
            if (existingRepo == null)
            {
                repo.UserId = authUser.Id;
                await repoRepo.AddAsync(repo);
            }
        }

        await _authUow.SaveChangesAsync();

        var result = reposJson.Select(r => new GitHubRepoDto(
            r.Name,
            r.HtmlUrl,
            r.Description
        ));

        return result;
    }



    public async Task<IEnumerable<GitHubPullRequestDto>> GetPullRequestsAsync(string userName, string repoName)
    {

        var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();
        var authUser = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == userName);
        if (authUser == null)
            throw new Exception($"User '{userName}' not found in database.");


        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", authUser.AccessToken);
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");


        var url = $"https://api.github.com/repos/{userName}/{repoName}/pulls?state=all";
        var response = await _httpClient.GetAsync(url);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            throw new Exception($"GitHub API error: {response.StatusCode} - {errorBody}");
        }


        var pullsFromGitHub = await response.Content.ReadFromJsonAsync<List<GitHubPullRequestDto>>(cancellationToken: CancellationToken.None);
        if (pullsFromGitHub == null)
            throw new Exception("GitHub returned null pull requests list.");


        var repoRepo = _authUow.GetGenericRepository<GitHubRepo, int>();
        var repository = await repoRepo.FirstOrDefaultAsync(r => r.Name == repoName && r.UserId == authUser.Id);
        if (repository == null)
            throw new Exception("Repository not found in database.");


        var prRepo = _authUow.GetGenericRepository<GitHubPullRequest, int>();
        foreach (var prDto in pullsFromGitHub)
        {
            var existingPr = await prRepo.FirstOrDefaultAsync(
                p => p.Number == prDto.Number &&
                     p.RepositoryId == repository.Id &&
                     p.UserId == authUser.Id
            );

            if (existingPr == null)
            {
                await prRepo.AddAsync(new GitHubPullRequest
                {
                    Number = prDto.Number,
                    Title = prDto.Title,
                   
                    State = prDto.State,
                    CreatedAt = prDto.CreatedAt,
                    RepositoryId = repository.Id,
                    UserId = authUser.Id
                });
            }
        }

        await _authUow.SaveChangesAsync();


        return pullsFromGitHub;
    }
    public async Task<GitHubPullRequestDto> GetPullRequest(string owner,int pullNumber,string repo)
{
    var userRepo =
        _authUow.GetGenericRepository<AuthUser, Guid>();

    var authUser =
        await userRepo.FirstOrDefaultAsync(
            u=>u.AuthUserName==owner);

    if(authUser==null)
        throw new Exception("User not found");

    _httpClient.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue(
            "Bearer",
            authUser.AccessToken);

    _httpClient.DefaultRequestHeaders.UserAgent
        .ParseAdd("Codience");

    var url =
$"https://api.github.com/repos/{owner}/{repo}/pulls/{pullNumber}";

    var response =
        await _httpClient.GetAsync(url);

    if(!response.IsSuccessStatusCode)
    {
        var error =
            await response.Content.ReadAsStringAsync();

        throw new Exception(
            $"GitHub error: {response.StatusCode} {error}");
    }

    return await response.Content
        .ReadFromJsonAsync<GitHubPullRequestDto>();
}
    public async Task<IEnumerable<GitHubFileDto>> GetChangedFilesAsync(string owner, string repo, int pullNumber)
    {
        var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();
        var authUser = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == owner);
        if (authUser == null)
            throw new Exception($"User '{owner}' not found in database.");

        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", authUser.AccessToken);
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");

        var url = $"https://api.github.com/repos/{owner}/{repo}/pulls/{pullNumber}/files";
        var response = await _httpClient.GetAsync(url);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            throw new Exception($"GitHub API error: {response.StatusCode} - {errorBody}");
        }

        var filesFromGitHub = await response.Content.ReadFromJsonAsync<List<GitHubFileDto>>(cancellationToken: CancellationToken.None);
        if (filesFromGitHub == null)
            throw new Exception("GitHub returned null changed files list.");

        return filesFromGitHub;
    }

    public async Task<IEnumerable<GitHubCommitDto>> GetCommitsByPath(string owner, string repo, string filePath)
    {
        var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();
        var authUser = await userRepo.FirstOrDefaultAsync(u => u.AuthUserName == owner);
        if (authUser == null)
            throw new Exception($"User '{owner}' not found in database.");

        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", authUser.AccessToken);
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Codience");

        var url = $"https://api.github.com/repos/{owner}/{repo}/commits?path={filePath}";
        var response = await _httpClient.GetAsync(url);
        if (!response.IsSuccessStatusCode)
        {
            var errorBody = await response.Content.ReadAsStringAsync();
            throw new Exception($"GitHub API error: {response.StatusCode} - {errorBody}");
        }

        var commitsFromGitHub = await response.Content.ReadFromJsonAsync<List<GitHubCommitDto>>(cancellationToken: CancellationToken.None);
        if (commitsFromGitHub == null)
            throw new Exception("GitHub returned null commits list.");

        return commitsFromGitHub;
    }

   public async Task<IEnumerable<GitHubCommitDto>> GetAllCommits(string owner,string repo, string author)
   {
    var userRepo = _authUow.GetGenericRepository<AuthUser, Guid>();

    var authUser = await userRepo
        .FirstOrDefaultAsync(u => u.AuthUserName == owner);

    if(authUser == null)
        throw new Exception("User not found");

    _httpClient.DefaultRequestHeaders.Authorization =
        new AuthenticationHeaderValue("Bearer", authUser.AccessToken);

    _httpClient.DefaultRequestHeaders.UserAgent
        .ParseAdd("Codience");

    var url =
        $"https://api.github.com/repos/{owner}/{repo}/commits?author={author}";

    var response = await _httpClient.GetAsync(url);

    response.EnsureSuccessStatusCode();

    var commits =
        await response.Content
        .ReadFromJsonAsync<List<GitHubCommitDto>>();

    return commits ?? new List<GitHubCommitDto>();
}
    public async Task<IEnumerable<GitHubCommitDto>>
GetPullRequestCommits(string owner,string repo,int pullNumber)
{
    var userRepo =
        _authUow.GetGenericRepository<AuthUser, Guid>();

    var authUser =
        await userRepo.FirstOrDefaultAsync(
            u=>u.AuthUserName==owner);

    if(authUser==null)
        throw new Exception("User not found");

    _httpClient.DefaultRequestHeaders.Authorization=
        new AuthenticationHeaderValue(
            "Bearer",
            authUser.AccessToken);

    _httpClient.DefaultRequestHeaders.UserAgent
        .ParseAdd("Codience");

    var url=
$"https://api.github.com/repos/{owner}/{repo}/pulls/{pullNumber}/commits";

    var response=
        await _httpClient.GetAsync(url);

    response.EnsureSuccessStatusCode();

    var commits=
        await response.Content
        .ReadFromJsonAsync<List<GitHubCommitDto>>();

    return commits ?? new List<GitHubCommitDto>();
}

}

