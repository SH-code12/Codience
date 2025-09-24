using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Infrastructure.Persistence.Migrations
{
    public partial class AlteronColumnCreatedAtPullREquest : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
             
            migrationBuilder.Sql(
                @"ALTER TABLE ""GitHub"".""PullRequests""
                  ALTER COLUMN ""CreatedAt"" TYPE timestamp with time zone
                  USING ""CreatedAt""::timestamp with time zone;"
            );
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
    
            migrationBuilder.Sql(
                @"ALTER TABLE ""GitHub"".""PullRequests""
                  ALTER COLUMN ""CreatedAt"" TYPE text
                  USING ""CreatedAt""::text;"
            );
        }
    }
}
