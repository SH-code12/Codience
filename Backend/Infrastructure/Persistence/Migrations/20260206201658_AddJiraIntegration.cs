using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class AddJiraIntegration : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "JiraAccessToken",
                table: "Users",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "JiraAccountId",
                table: "Users",
                type: "text",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "JiraIssues",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    JiraKey = table.Column<string>(type: "text", nullable: false),
                    IssueType = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_JiraIssues", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "GitHubPullRequestJiraIssue",
                columns: table => new
                {
                    JiraIssuesId = table.Column<int>(type: "integer", nullable: false),
                    PullRequestsId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_GitHubPullRequestJiraIssue", x => new { x.JiraIssuesId, x.PullRequestsId });
                    table.ForeignKey(
                        name: "FK_GitHubPullRequestJiraIssue_JiraIssues_JiraIssuesId",
                        column: x => x.JiraIssuesId,
                        principalTable: "JiraIssues",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_GitHubPullRequestJiraIssue_PullRequests_PullRequestsId",
                        column: x => x.PullRequestsId,
                        principalSchema: "GitHub",
                        principalTable: "PullRequests",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_GitHubPullRequestJiraIssue_PullRequestsId",
                table: "GitHubPullRequestJiraIssue",
                column: "PullRequestsId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "GitHubPullRequestJiraIssue");

            migrationBuilder.DropTable(
                name: "JiraIssues");

            migrationBuilder.DropColumn(
                name: "JiraAccessToken",
                table: "Users");

            migrationBuilder.DropColumn(
                name: "JiraAccountId",
                table: "Users");
        }
    }
}
