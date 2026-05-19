using Core.Abstraction;
using Share;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Core.Services;
using Infrastructure.Persistence.Data;
using Infrastructure.Persistence.Repositories;
using Infrastructure.Presentation.Controllers;
using Microsoft.EntityFrameworkCore;
using dotenv.net;

// =====================================================
// Load .env
// =====================================================

DotEnv.Fluent()
    .WithEnvFiles("../.env")
    .Load();

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddEnvironmentVariables();


// =====================================================
// Database
// =====================================================

var connectionString =
    Environment.GetEnvironmentVariable("ConnectionStrings__DefaultConnection")
    ?? throw new InvalidOperationException("Connection string not found.");

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

// =====================================================
// Controllers & Swagger
// =====================================================

builder.Services.AddOpenApi();

builder.Services.AddControllers()
       .AddApplicationPart(typeof(GitHubAuthController).Assembly)
       .AddApplicationPart(typeof(JiraController).Assembly);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();


// =====================================================
// CORS
// =====================================================

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});


// =====================================================
// Dependency Injection
// =====================================================

builder.Services.AddScoped<IReviewerService, ReviewerService>();

builder.Services.AddScoped<IChangeMetricsService, ChangeMetricsService>();

builder.Services.AddScoped<IHistoryMetricsService, HistoryMetricsService>();

builder.Services.AddScoped<IExperienceMetricsService, ExperienceMetricsService>();

builder.Services.AddScoped<IGitHubWebhookService, GithubWebhookService>();

builder.Services.AddScoped<GitHubJwtProvider>();

builder.Services.AddScoped<IPRCommitsService, PRCommitsService>();

builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();

builder.Services.AddScoped<IGitHubAppService, GitHubAppService>();

builder.Services.AddScoped<IRiskService, RiskService>();

builder.Services.AddScoped<CsvProcessor>();

builder.Services.AddScoped(
    typeof(IGenericRepository<AuthUser, Guid>),
    typeof(GenericRepository<AuthUser, Guid>)
);


// =====================================================
// Http Clients
// =====================================================

builder.Services.AddHttpClient<IGithubAuthService, GitHubAuthService>();

builder.Services.AddHttpClient<IJiraService, JiraService>();

builder.Services.AddHttpClient("FastApiClient", client =>
{
    client.BaseAddress = new Uri("http://127.0.0.1:8000/");
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

builder.Services.AddHttpClient("ReviewerApiClient", client =>
{
    client.BaseAddress = new Uri("http://127.0.0.1:8000/");
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});


// =====================================================
// Build App
// =====================================================

var app = builder.Build();


// =====================================================
// Middleware
// =====================================================

app.UseCors("AllowAll");

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();

    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

app.MapControllers();


// =====================================================
// Auto Migration
// =====================================================

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


// =====================================================
// Run
// =====================================================

app.Run();