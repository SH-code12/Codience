namespace Share;

public class PagedResult<T>
{
    public IEnumerable<T> Items { get; set; }= new List<T>();
    public int Page { get; set; }
    public int PageSize { get; set; }
    public bool HasNextPage { get; set; }

    public PagedResult(IEnumerable<T> items,  int page, int pageSize, bool hasNextPage)
    {
        Items = items;
        Page = page;
        PageSize = pageSize;
        HasNextPage = hasNextPage;
    }
}
