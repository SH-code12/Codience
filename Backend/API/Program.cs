using Core.Abstraction;
using Share;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Core.Services;
using Infrastructure.Persistence.Data;
using Infrastructure.Persistence.Repositories;
using Infrastructure.Presentation.Controllers;
using Microsoft.EntityFrameworkCore;
using Infrastructure.Presentation;
using Infrastructure.Presentation.Hubs;
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
        policy
            .SetIsOriginAllowed(_ => true) // Allow any origin
            .AllowAnyHeader()
            .AllowAnyMethod()
            .AllowCredentials();
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

builder.Services.AddSingleton<GitHubJwtProvider>();

builder.Services.AddScoped<IPRCommitsService, PRCommitsService>();

builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();

builder.Services.AddScoped<IGitHubAppService, GitHubAppService>();

builder.Services.AddScoped<IAnalyticsService, AnalyticsService>();

builder.Services.AddScoped<IRiskService, RiskService>();

builder.Services.AddScoped<CsvProcessor>();

builder.Services.AddScoped(
    typeof(IGenericRepository<, >),
    typeof(GenericRepository<, >)

);

builder.Services.AddSignalR();
builder.Services.AddScoped<IRealTimeNotification,RealTimeNotification>();


// =====================================================
// Http Clients
// =====================================================

builder.Services.AddHttpClient<IGithubAuthService, GitHubAuthService>();

builder.Services.AddHttpClient<IJiraService, JiraService>();

builder.Services.AddHttpClient<IProfilingService, GithubProfilingService>();

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


app.UseHttpsRedirection();

app.UseRouting(); 

app.UseCors("AllowAll");

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();

    app.UseSwagger();
    app.UseSwaggerUI();
}


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
//===SIGNALR HUBS===
app.MapHub<PullRequestHub>("/hubs/pullrequests");


// =====================================================
// Run
// =====================================================

app.Run();