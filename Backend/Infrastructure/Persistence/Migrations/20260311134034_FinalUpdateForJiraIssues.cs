using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class FinalUpdateForJiraIssues : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_GitHubPullRequestJiraIssue_JiraIssues_JiraIssuesId",
                table: "GitHubPullRequestJiraIssue");

            migrationBuilder.DropForeignKey(
                name: "FK_GitHubPullRequestJiraIssue_PullRequests_PullRequestsId",
                table: "GitHubPullRequestJiraIssue");

            migrationBuilder.DropPrimaryKey(
                name: "PK_GitHubPullRequestJiraIssue",
                table: "GitHubPullRequestJiraIssue");

            migrationBuilder.EnsureSchema(
                name: "Jira");

            migrationBuilder.RenameTable(
                name: "JiraIssues",
                newName: "JiraIssues",
                newSchema: "Jira");

            migrationBuilder.RenameTable(
                name: "GitHubPullRequestJiraIssue",
                newName: "PRJiraLinks",
                newSchema: "Jira");

            migrationBuilder.RenameIndex(
                name: "IX_GitHubPullRequestJiraIssue_PullRequestsId",
                schema: "Jira",
                table: "PRJiraLinks",
                newName: "IX_PRJiraLinks_PullRequestsId");

            migrationBuilder.AlterColumn<string>(
                name: "JiraKey",
                schema: "Jira",
                table: "JiraIssues",
                type: "character varying(50)",
                maxLength: 50,
                nullable: false,
                oldClrType: typeof(string),
                oldType: "text");

            migrationBuilder.AddColumn<string>(
                name: "Priority",
                schema: "Jira",
                table: "JiraIssues",
                type: "text",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "Status",
                schema: "Jira",
                table: "JiraIssues",
                type: "text",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "Summary",
                schema: "Jira",
                table: "JiraIssues",
                type: "text",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<Guid>(
                name: "UserId",
                schema: "Jira",
                table: "JiraIssues",
                type: "uuid",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"));

            migrationBuilder.AddPrimaryKey(
                name: "PK_PRJiraLinks",
                schema: "Jira",
                table: "PRJiraLinks",
                columns: new[] { "JiraIssuesId", "PullRequestsId" });

            migrationBuilder.CreateIndex(
                name: "IX_JiraIssues_JiraKey",
                schema: "Jira",
                table: "JiraIssues",
                column: "JiraKey",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_JiraIssues_UserId",
                schema: "Jira",
                table: "JiraIssues",
                column: "UserId");

            migrationBuilder.AddForeignKey(
                name: "FK_JiraIssues_Users_UserId",
                schema: "Jira",
                table: "JiraIssues",
                column: "UserId",
                principalTable: "Users",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.AddForeignKey(
                name: "FK_PRJiraLinks_JiraIssues_JiraIssuesId",
                schema: "Jira",
                table: "PRJiraLinks",
                column: "JiraIssuesId",
                principalSchema: "Jira",
                principalTable: "JiraIssues",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.AddForeignKey(
                name: "FK_PRJiraLinks_PullRequests_PullRequestsId",
                schema: "Jira",
                table: "PRJiraLinks",
                column: "PullRequestsId",
                principalSchema: "GitHub",
                principalTable: "PullRequests",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_JiraIssues_Users_UserId",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.DropForeignKey(
                name: "FK_PRJiraLinks_JiraIssues_JiraIssuesId",
                schema: "Jira",
                table: "PRJiraLinks");

            migrationBuilder.DropForeignKey(
                name: "FK_PRJiraLinks_PullRequests_PullRequestsId",
                schema: "Jira",
                table: "PRJiraLinks");

            migrationBuilder.DropIndex(
                name: "IX_JiraIssues_JiraKey",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.DropIndex(
                name: "IX_JiraIssues_UserId",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.DropPrimaryKey(
                name: "PK_PRJiraLinks",
                schema: "Jira",
                table: "PRJiraLinks");

            migrationBuilder.DropColumn(
                name: "Priority",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.DropColumn(
                name: "Status",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.DropColumn(
                name: "Summary",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.DropColumn(
                name: "UserId",
                schema: "Jira",
                table: "JiraIssues");

            migrationBuilder.RenameTable(
                name: "JiraIssues",
                schema: "Jira",
                newName: "JiraIssues");

            migrationBuilder.RenameTable(
                name: "PRJiraLinks",
                schema: "Jira",
                newName: "GitHubPullRequestJiraIssue");

            migrationBuilder.RenameIndex(
                name: "IX_PRJiraLinks_PullRequestsId",
                table: "GitHubPullRequestJiraIssue",
                newName: "IX_GitHubPullRequestJiraIssue_PullRequestsId");

            migrationBuilder.AlterColumn<string>(
                name: "JiraKey",
                table: "JiraIssues",
                type: "text",
                nullable: false,
                oldClrType: typeof(string),
                oldType: "character varying(50)",
                oldMaxLength: 50);

            migrationBuilder.AddPrimaryKey(
                name: "PK_GitHubPullRequestJiraIssue",
                table: "GitHubPullRequestJiraIssue",
                columns: new[] { "JiraIssuesId", "PullRequestsId" });

            migrationBuilder.AddForeignKey(
                name: "FK_GitHubPullRequestJiraIssue_JiraIssues_JiraIssuesId",
                table: "GitHubPullRequestJiraIssue",
                column: "JiraIssuesId",
                principalTable: "JiraIssues",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.AddForeignKey(
                name: "FK_GitHubPullRequestJiraIssue_PullRequests_PullRequestsId",
                table: "GitHubPullRequestJiraIssue",
                column: "PullRequestsId",
                principalSchema: "GitHub",
                principalTable: "PullRequests",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
