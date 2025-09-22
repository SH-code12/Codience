

using Core.Domain.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Infrastructure.Persistence.Data.Configuration;

public class AuthUserConfigurations : IEntityTypeConfiguration<AuthUser>
{
    public void Configure(EntityTypeBuilder<AuthUser> builder)
    {
        builder.ToTable("Users", "Auth");

        builder.Property(u => u.Email)
              .IsRequired()
              .HasMaxLength(100);
        builder.Property(u => u.GitHubId)
               .IsRequired();
        builder.HasMany(u => u.Repositories)
               .WithOne(r => r.User)
               .HasForeignKey(r => r.UserId);

        builder.HasMany(u => u.PullRequests)
               .WithOne(p => p.User)
               .HasForeignKey(p => p.UserId);
        
    }
}
