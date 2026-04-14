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

        // Users
        modelBuilder.Entity<User>(e =>
        {
            e.HasIndex(u => u.Username).IsUnique();
            e.Property(u => u.PasswordHash).IsRequired();
            e.Property(u => u.IsActive).HasDefaultValue(true);
            e.Property(u => u.IsAdmin).HasDefaultValue(false);
        });

        // Groups
        modelBuilder.Entity<Group>(e =>
        {
            e.HasIndex(g => g.Name).IsUnique();
        });

        // UserGroups — composite PK, cascade on user delete, restrict on group delete
        modelBuilder.Entity<UserGroup>(e =>
        {
            e.HasKey(ug => new { ug.UserId, ug.GroupId });
            e.HasOne(ug => ug.User)
                .WithMany(u => u.UserGroups)
                .HasForeignKey(ug => ug.UserId)
                .OnDelete(DeleteBehavior.Cascade);
            e.HasOne(ug => ug.Group)
                .WithMany(g => g.UserGroups)
                .HasForeignKey(ug => ug.GroupId)
                .OnDelete(DeleteBehavior.Restrict);
        });

        // AuditEvents — index on Timestamp for query performance
        modelBuilder.Entity<AuditEvent>(e =>
        {
            e.HasIndex(a => a.Timestamp);
        });

        // Seed default groups
        modelBuilder.Entity<Group>().HasData(
            new Group { Id = 1, Name = "PM" },
            new Group { Id = 2, Name = "RM" }
        );
    }
}
