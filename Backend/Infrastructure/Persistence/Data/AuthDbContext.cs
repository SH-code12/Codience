

using Core.Domain.Models;
using Microsoft.EntityFrameworkCore;
using Persistence;



namespace Infrastructure.Persistence.Data;

public class AuthDbContext (DbContextOptions<AuthDbContext> options) : DbContext(options) 
{

    public DbSet<AuthUser> Users { get; set; }
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(AssemblyReference).Assembly);
    }

}
