using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace FinLens.Web.Migrations;

public partial class AddAnalysisStep : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder) =>
        migrationBuilder.AddColumn<string>(
            name: "Step",
            table: "Analyses",
            type: "text",
            nullable: true);

    protected override void Down(MigrationBuilder migrationBuilder) =>
        migrationBuilder.DropColumn(name: "Step", table: "Analyses");
}
