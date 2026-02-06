using Core.Domain.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

public class JiraConfigurations : IEntityTypeConfiguration<JiraIssue>
{
    public void Configure(EntityTypeBuilder<JiraIssue> builder)
    {
        builder.ToTable("JiraIssues", "Jira");
        
       
        builder.HasKey(j => j.Id); 

       
        builder.Property(j => j.JiraKey).IsRequired().HasMaxLength(50);
        builder.HasIndex(j => j.JiraKey).IsUnique();

        builder.HasMany(j => j.PullRequests)
               .WithMany(p => p.JiraIssues)
               .UsingEntity(t => t.ToTable("PRJiraLinks", "Jira"));
    }
}