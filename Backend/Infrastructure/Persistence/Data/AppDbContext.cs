using Core.Domain.Models;
using Microsoft.EntityFrameworkCore;

namespace Infrastructure.Persistence.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

        public DbSet<GitHubRepo> Repositories { get; set; }
        public DbSet<GitHubPullRequest> PullRequests { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            modelBuilder.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly);
        }
    }
}
