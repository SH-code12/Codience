

namespace Core.Domain.Models;


public class AuthUser : BaseEntity<Guid>
{


        public string GitHubId { get; set; } = default!;
        public string AuthUserName { get; set; } = default!;
        public string Email { get; set; } = default!;
        public string? AccessToken { get; set; } = default!;
         public string? Password { get; set; } = default!;
    
}
