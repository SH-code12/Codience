using Core.Abstraction;
using Share;

public class ExperienceMetricsService : IExperienceMetricsService
{
    private readonly IGithubAuthService _git;

    public ExperienceMetricsService(IGithubAuthService git)
    {
        _git = git;
    }

    public async Task<ExperienceMetricsDto>
        CalculateExperienceMetrics(
        string owner,
        string repo,
        int pullNumber)
    {

        var pr=await _git.GetPullRequest(owner,pullNumber,repo);

        var author=pr.User.Login;

        var allCommits=
            await _git.GetAllCommits(owner,repo,author);

        var prCommits=
            await _git.GetPullRequestCommits(owner,repo,pullNumber);

        var files=
            await _git.GetChangedFilesAsync(owner,repo,pullNumber);

        var exp=allCommits.Count();

        var rexp=CalculateRecentExperience(allCommits);

        var sexp=
            await CalculateSubsystemExperience(
                owner,
                repo,
                author,
                files);

        return new ExperienceMetricsDto
        {
            EXP=exp,
            REXP=rexp,
            SEXP=sexp
        };

    }

    private double CalculateRecentExperience(
        IEnumerable<GitHubCommitDto> commits)
    {

        double result=0;

        foreach(var commit in commits)
        {
            var age=(DateTime.UtcNow-
                commit.Commit.Author.Date).TotalDays;

            result+=1/(1+age);
        }

        return result;
    }

    private async Task<int>
        CalculateSubsystemExperience(
        string owner,
        string repo,
        string author,
        IEnumerable<GitHubFileDto> files)
    {

        int count=0;

        foreach(var file in files)
        {
            var commits=
                await _git.GetCommitsByPath(
                    owner,
                    repo,
                    file.Filename);

            count+=commits
                .Where(c=>c.Author.Login==author)
                .Count();
        }

        return count;
    }

}