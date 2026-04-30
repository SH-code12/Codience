using Share;

namespace Core.Abstraction;

public interface  IPRCommitsService
{
     Task<IEnumerable<PRCommitDto>> CalculateAsync(string owner,string repo,int pullNumber);
      //Task<CommitChangesDto> GetChangesAsync(string owner, string repo,string commitSha);
}
