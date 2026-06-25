using Core.Domain.Contracts;
using Core.Domain.Models;
using Microsoft.AspNetCore.SignalR;
using System.Security.Claims;

namespace Infrastructure.Presentation.Hubs;

public class PullRequestHub : Hub
{
    private readonly IUnitOfWork _uow;

    public PullRequestHub(IUnitOfWork uow)
    {
        _uow = uow;
    }

public async Task RegisterRepository(
    Guid userId,
    string owner,
    string repoName)
{
    try
    {
        Console.WriteLine("START REGISTER");

        var repo =
            _uow.GetGenericRepository<UserConnection, int>();

        await repo.AddAsync(new UserConnection
        {
            UserId = userId,
            ConnectionId = Context.ConnectionId,
            Owner = owner,
            RepoName = repoName
        });

        await _uow.SaveChangesAsync();

        Console.WriteLine("REGISTER SUCCESS");
    }
    catch(Exception ex)
    {
        Console.WriteLine(ex.ToString());
        throw;
    }
}



    public override async Task OnDisconnectedAsync(
        Exception? exception)
    {
        var repo =
            _uow.GetGenericRepository<UserConnection, int>();

        var connections = await repo.GetAllAsync();

        var current = connections
            .FirstOrDefault(x =>
                x.ConnectionId == Context.ConnectionId);

        if (current != null)
        {
            await repo.RemoveAsync(current);

            await _uow.SaveChangesAsync();
        }

        await base.OnDisconnectedAsync(exception);
         Console.WriteLine(
        $"DISCONNECTED => {Context.ConnectionId}");
    }
}