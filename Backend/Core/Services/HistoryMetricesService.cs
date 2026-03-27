using Core.Abstraction;
using Share;

namespace Core.Services;

public class HistoryMetricsService : IHistoryMetricsService
{
    private readonly IGithubAuthService _gitHubService;

    public HistoryMetricsService(IGithubAuthService gitHubService)
    {
        _gitHubService = gitHubService;
    }

    public async Task<HistoryMetricsDto> Calculate(
        string owner,
        string repo,
        int pullNumber)
    {
        var files = await _gitHubService.GetChangedFilesAsync(owner, repo, pullNumber);

        var allDevelopers = new HashSet<string>();
        int totalCommits = 0;
        DateTime? latestCommitDate = null;

        foreach (var file in files)
        {
            var commits = await _gitHubService.GetCommitsByPath(owner, repo, file.Filename);

            foreach (var commit in commits)
            {
                if (!string.IsNullOrEmpty(commit.AuthorLogin))
                    allDevelopers.Add(commit.AuthorLogin);

                totalCommits++;

                if (latestCommitDate == null || commit.CommitDate > latestCommitDate)
                    latestCommitDate = commit.CommitDate;
            }
        }

        // NDEV
        var ndev = allDevelopers.Count;

        //  NUC
        var nuc = totalCommits;

        // AGE (days since last change)
        double age = 0;

        if (latestCommitDate.HasValue)
        {
            age = (DateTime.UtcNow - latestCommitDate.Value).TotalDays;
        }

        return new HistoryMetricsDto
        {
            NDEV = ndev,
            NUC = nuc,
            AGE = age
        };
    }
}
