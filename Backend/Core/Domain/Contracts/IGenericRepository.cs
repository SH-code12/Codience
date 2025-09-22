using System.Linq.Expressions;
using Core.Domain.Models;

namespace Core.Domain.Contracts;

public interface IGenericRepository<TEntity, TKey> where TEntity : BaseEntity<TKey>
where TKey : IEquatable<TKey>

{
    Task<TEntity?> GetByIdAsync(TKey id);
    Task<IEnumerable<TEntity>> GetAllAsync();
    Task AddAsync(TEntity entity);
    Task<TEntity?> FirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate);

    
}
