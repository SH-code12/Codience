using Core.Domain.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Infrastructure.Persistence.Data.Configuration;

public class RepositoryConfigurations:IEntityTypeConfiguration<GitHubRepo>
{
     public void Configure(EntityTypeBuilder<GitHubRepo> builder)
    {
        builder.ToTable("Repository","GitHub");
        builder.HasKey(r => r.Id);

        builder.Property(r => r.Name)
            .IsRequired()
            .HasMaxLength(200);

        builder.Property(r => r.HtmlUrl)
            .IsRequired();

        builder.Property(r => r.Description)
            .HasMaxLength(1000);

        builder.HasMany(r => r.PullRequests)
                  .WithOne(p => p.Repository)            // علاقة One Repo → Many PRs
                  .HasForeignKey(p => p.RepositoryId);   // الـ FK في PR
                  
    }

   

}
