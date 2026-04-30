using Core.Abstraction;
using Share;

namespace Core.Services;

public class PRCommitsService : IPRCommitsService
{
    private readonly IGithubAuthService _git;
    private readonly IChangeMetricsService _change;

    public PRCommitsService(IGithubAuthService git,IChangeMetricsService change)
    {
        _git = git;
        _change = change;
    }

    public async Task<IEnumerable<PRCommitDto>> CalculateAsync(string owner,string repo, int pullNumber)
    {
        var commits = (await _git.GetPullRequestCommits(owner, repo, pullNumber)).ToList();
        
        int totalCommits = commits.Count;

        var result = new List<PRCommitDto>();

        foreach (var commit in commits)
        {
            var files = (await _git.GetChangedFilesAsync(owner, repo, int.Parse(commit.Sha))).ToList();

            var experience = new ExperienceMetricsDto
            {
                EXP = 1,

                REXP = 1 / (1 + (DateTime.UtcNow - commit.CommitDate).TotalDays),

                SEXP = commits
                    .Count(c => c.AuthorLogin == commit.AuthorLogin)
            };

            
            var history = new HistoryMetricsDto
            {
                NDEV = commits
                    .Select(c => c.AuthorLogin)
                    .Distinct()
                    .Count(),

                NUC = 1,

                AGE = (DateTime.UtcNow - commit.CommitDate).TotalDays
            };

           
            var change = _change.Calculate(files);

            result.Add(new PRCommitDto
            {
                CommitSha = commit.Sha,
                Author = commit.AuthorLogin,
                Date = commit.CommitDate,

                Experience = experience,
                History = history,
                Change = change
            });
        }

        return result;
    }

}