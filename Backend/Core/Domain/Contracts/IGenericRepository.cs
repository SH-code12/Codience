using Core.Domain.Models;

namespace Core.Domain.Contracts;

public interface IGenericRepository<TEntity,TKey> where TEntity : BaseEntity<TKey>
where TKey:IEquatable<TKey>

{
     Task<TEntity?> GetByIdAsync(TKey id);
    Task<IEnumerable<TEntity>> GetAllAsync();
   
}
