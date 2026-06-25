using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Infrastructure.Presentation.Hubs;
using Microsoft.AspNetCore.SignalR;
using Share;

namespace Infrastructure.Presentation;

public class RealTimeNotification
    : IRealTimeNotification
{
    private readonly IHubContext<PullRequestHub> _hub;

    private readonly IGenericRepository<UserConnection,int> _connectionRepo;

    public RealTimeNotification(IHubContext<PullRequestHub> hub,IGenericRepository<UserConnection, int> connectionRepo)
    {
        _hub = hub;
        _connectionRepo = connectionRepo;
    }

    public async Task NotifyPullRequestCreatedAsync(GitHubPullRequestDto data)
    {

        Console.WriteLine($"Notifying clients about new pull request: {data.Title} in repository {data.RepositoryName} owned by {data.Owner}");
        var allConnections =
            await _connectionRepo.GetAllAsync();
        Console.WriteLine($"Found {allConnections.Count()} connections");

        var targets = allConnections
            .Where(x =>
                x.Owner == data.Owner &&
                x.RepoName == data.RepositoryName)
            .ToList();

        Console.WriteLine($"Found {targets.Count()} matching connections");

        foreach (var target in targets)
        {
            await _hub.Clients
                .Client(target.ConnectionId)
                .SendAsync(
                    "PullRequestCreated",
                    data);
        }
    }
}