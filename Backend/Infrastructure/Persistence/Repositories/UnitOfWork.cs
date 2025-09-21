using System.Reflection.Metadata.Ecma335;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Infrastructure.Persistence.Data;

namespace Infrastructure.Persistence.Repositories;

public class UnitOfWork : IUnitOfWork
{
     private readonly AppDbContext context;
    private readonly Dictionary<string, object> _repositories = [];

     public UnitOfWork(AppDbContext context)
    {
        this.context = context;
    }
    public IGenericRepository<TEntity, TKey> GetGenericRepository<TEntity, TKey>()
        where TEntity : BaseEntity<TKey>
        where TKey : IEquatable<TKey>
    {
        var typeName = typeof(TEntity).Name;
        if (_repositories.ContainsKey(typeName))
            return (IGenericRepository<TEntity, TKey>)_repositories[typeName];
        var Repo = new GenericRepository<TEntity, TKey>(context);
        _repositories[typeName] = Repo;
        return Repo;
    }

    public async Task<int> SaveChangesAsync() => await context.SaveChangesAsync();
   
}
