using Finadoc.Web.Models;
using Microsoft.EntityFrameworkCore;

namespace Finadoc.Web.Data;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<User> Users => Set<User>();
    public DbSet<Group> Groups => Set<Group>();
    public DbSet<UserGroup> UserGroups => Set<UserGroup>();
    public DbSet<Document> Documents => Set<Document>();
    public DbSet<Analysis> Analyses => Set<Analysis>();
    public DbSet<AuditEvent> AuditEvents => Set<AuditEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Composite PK for the join table
        modelBuilder.Entity<UserGroup>()
            .HasKey(ug => new { ug.UserId, ug.GroupId });

        // Seed default groups
        modelBuilder.Entity<Group>().HasData(
            new Group { Id = 1, Name = "PM" },
            new Group { Id = 2, Name = "RM" }
        );
    }
}
