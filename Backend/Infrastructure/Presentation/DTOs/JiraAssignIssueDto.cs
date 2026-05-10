namespace Infrastructure.Presentation.DTOs
{
    public class JiraAssignIssueDto
    {
        public string Token { get; set; } = string.Empty;
        public string CloudId { get; set; } = string.Empty;
        public string AccountId { get; set; } = string.Empty;

        public string IssueKey { get; set; } = string.Empty;
        public string AssigneeId { get; set; } = string.Empty;
    }
}