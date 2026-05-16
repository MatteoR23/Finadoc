using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace FinLens.Web.Migrations;

public partial class AddAgenticAnalysisFields : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<string>(
            name: "Goal",
            table: "Analyses",
            type: "text",
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "Mode",
            table: "Analyses",
            type: "text",
            nullable: false,
            defaultValue: "Standard");

        migrationBuilder.AddColumn<string>(
            name: "PlanS3Key",
            table: "Analyses",
            type: "text",
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "ReportS3Key",
            table: "Analyses",
            type: "text",
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "ResultS3Key",
            table: "Analyses",
            type: "text",
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "TraceS3Key",
            table: "Analyses",
            type: "text",
            nullable: true);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropColumn(name: "Goal", table: "Analyses");
        migrationBuilder.DropColumn(name: "Mode", table: "Analyses");
        migrationBuilder.DropColumn(name: "PlanS3Key", table: "Analyses");
        migrationBuilder.DropColumn(name: "ReportS3Key", table: "Analyses");
        migrationBuilder.DropColumn(name: "ResultS3Key", table: "Analyses");
        migrationBuilder.DropColumn(name: "TraceS3Key", table: "Analyses");
    }
}
