using System.Linq.Expressions;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Infrastructure.Persistence.Data;
using Microsoft.EntityFrameworkCore;

namespace Infrastructure.Persistence.Repositories;

public class GenericRepository<TEntity, TKey>
: IGenericRepository<TEntity, TKey>
where TEntity : BaseEntity<TKey>
where TKey : IEquatable<TKey>

{
  protected readonly AppDbContext _context;

  public GenericRepository(AppDbContext context)
  {
    _context = context;
  }

  public async Task AddAsync(TEntity entity)
              => await _context.Set<TEntity>().AddAsync(entity);



  public async Task<IEnumerable<TEntity>> GetAllAsync()
              => await _context.Set<TEntity>().ToListAsync();


  public async Task<TEntity?> GetByIdAsync(TKey id)
         => await _context.Set<TEntity>().FindAsync(id);

  public async Task<TEntity?> FirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate)

   => await _context.Set<TEntity>().FirstOrDefaultAsync(predicate);


}