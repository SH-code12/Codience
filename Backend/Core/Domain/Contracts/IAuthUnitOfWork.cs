using Core.Domain.Models;

namespace Core.Domain.Contracts;

public interface IAuthUnitOfWork
{
    Task<int> SaveChangesAsync();
    IGenericRepository<TEntity, TKey> GetGenericRepository<TEntity, TKey>()
    where TEntity : BaseEntity<TKey>
    where TKey : IEquatable<TKey>;
    

}
