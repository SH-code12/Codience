using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Core.Services;
using Infrastructure.Persistence.Data;
using Infrastructure.Persistence.Repositories;
using Infrastructure.Presentation.Controllers;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddOpenApi();
builder.Services.AddControllers()
       .AddApplicationPart(typeof(GitHubAuthController).Assembly);

// Configure DbContext with connection string
var connectionString = Environment.GetEnvironmentVariable("ConnectionStrings__DefaultConnection")
                      ?? builder.Configuration.GetConnectionString("DefaultConnection");
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

// Add scoped services and HttpClient
builder.Services.AddHttpClient<IGithubAuthService, GitHubAuthService>();
builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();
builder.Services.AddScoped(typeof(IGenericRepository<AuthUser, Guid>), typeof(GenericRepository<AuthUser, Guid>));
builder.Services.AddHttpClient("FastApiClient", client =>
{
    client.BaseAddress = new Uri("https://fordless-samella-unexpendable.ngrok-free.dev/"); // Replace with actual ngrok URL
    client.Timeout = TimeSpan.FromSeconds(30);
});
builder.Services.AddScoped<IRiskService, RiskService>();
builder.Services.AddScoped<CsvProcessor>();

// Configure CORS (restrictive policy for production)
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowSpecificOrigins", policy =>
    {
        policy.WithOrigins("https://your-frontend-domain.com") // Specify allowed origins
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials(); // If your app uses credentials (e.g., cookies, auth tokens)
    });
});

// Add Swagger for API exploration
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();


app.UseHttpsRedirection();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage(); // Detailed error pages for development
    app.UseSwagger();
    app.UseSwaggerUI();
}



app.UseCors("AllowAll");

app.MapControllers();





using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;
    var db = services.GetRequiredService<AppDbContext>();
    var apply = Environment.GetEnvironmentVariable("APPLY_MIGRATIONS");
    if (apply == "true")
    {
        db.Database.Migrate();
    }
}

app.Run();