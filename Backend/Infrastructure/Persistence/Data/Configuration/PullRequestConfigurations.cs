using Core.Domain.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Infrastructure.Persistence.Data.Configuration;

public class PullRequestConfigurations : IEntityTypeConfiguration<GitHubPullRequest>
{
    public void Configure(EntityTypeBuilder<GitHubPullRequest> builder)
    {
        builder.ToTable("PullRequests","GitHub");

        builder.HasKey(p => p.Id);
        builder.Property(P => P.Id).UseIdentityColumn();

        builder.Property(p => p.Title)
            .IsRequired()
            .HasMaxLength(300);

     

        builder.Property(p => p.State)
            .IsRequired()
            .HasMaxLength(50);

        builder.Property(p => p.CreatedAt)
            .IsRequired();
      
    }
    
}
