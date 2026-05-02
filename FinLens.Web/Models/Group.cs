namespace FinLens.Web.Models;

/// <summary>Valid group names: "PM", "RM", "DQ".</summary>
public class Group
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;

    public ICollection<UserGroup> UserGroups { get; set; } = [];
}
