using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace FinLens.Web.Migrations;

public partial class AddDqGroup : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder) =>
        migrationBuilder.InsertData(
            table: "Groups",
            columns: ["Id", "Name"],
            values: new object[] { 3, "DQ" });

    protected override void Down(MigrationBuilder migrationBuilder) =>
        migrationBuilder.DeleteData(
            table: "Groups",
            keyColumn: "Id",
            keyValue: 3);
}
