namespace Finadoc.Web.Models;

public class UserGroup
{
    public Guid UserId { get; set; }
    public User User { get; set; } = null!;

    public int GroupId { get; set; }
    public Group Group { get; set; } = null!;
}
