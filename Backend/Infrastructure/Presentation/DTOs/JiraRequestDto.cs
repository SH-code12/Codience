namespace Infrastructure.Presentation.DTOs
{
    public class JiraRequestDto
    {
        public string Token { get; set; } = string.Empty;
        public string CloudId { get; set; } = string.Empty;
        public string ProjectKey { get; set; } = string.Empty;
        public string AssigneeName { get; set; } = string.Empty;

        public string Summary { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string IssueType { get; set; } = string.Empty;
    }
}