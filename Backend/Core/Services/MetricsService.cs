
using Share;

public interface IChangeMetricsService
{
    ChangeMetricsDto Calculate(IEnumerable<GitHubFileDto> files);
}

public class ChangeMetricsService : IChangeMetricsService
{
    public ChangeMetricsDto Calculate(IEnumerable<GitHubFileDto> files)
    {
        var fileList = files.ToList();

        if (!fileList.Any())
            return new ChangeMetricsDto();

        
        var nf = fileList.Count;

    
        var nd = fileList
            .Select(f => GetDirectory(f.Filename))
            .Where(d => !string.IsNullOrEmpty(d))
            .Distinct()
            .Count();

        
        var ns = fileList
            .Select(f => GetSubsystem(f.Filename))
            .Where(s => !string.IsNullOrEmpty(s))
            .Distinct()
            .Count();

        var la = fileList.Sum(f => f.Additions);
        var ld = fileList.Sum(f => f.Deletions);

        // ✅ Entropy
        var totalChanges = fileList.Sum(f => f.Additions + f.Deletions);

        double entropy = 0;

        if (totalChanges > 0)
        {
            entropy = fileList.Sum(f =>
            {
                var changes = f.Additions + f.Deletions;
                if (changes == 0) return 0;

                var pi = (double)changes / totalChanges;
                return -pi * Math.Log2(pi);
            });
        }

        return new ChangeMetricsDto
        {
            NFiles = nf,
            NDirectories = nd,
            NSubsystems = ns,
            LinesAdded = la,
            LinesDeleted = ld,
            Entropy = entropy
        };
    }

    private string GetDirectory(string path)
    {
        if (string.IsNullOrEmpty(path) || !path.Contains("/"))
            return string.Empty;

        return path.Substring(0, path.LastIndexOf('/'));
    }

    private string GetSubsystem(string path)
    {
        if (string.IsNullOrEmpty(path))
            return string.Empty;

        return path.Split('/')[0];
    }
}