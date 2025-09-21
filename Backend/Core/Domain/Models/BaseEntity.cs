namespace Core.Domain.Models;

public abstract class BaseEntity<TKey> where TKey :IEquatable<TKey>
{
    public TKey Id { get; set; } = default!;
}