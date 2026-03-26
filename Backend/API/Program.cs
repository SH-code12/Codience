using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Core.Services;
using Infrastructure.Persistence.Data;
using Infrastructure.Persistence.Repositories;
using Infrastructure.Presentation.Controllers;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();
builder.Services.AddControllers()
       .AddApplicationPart(typeof(GitHubAuthController).Assembly)
       .AddApplicationPart(typeof(JiraController).Assembly); 

var fastApiConfig = builder.Configuration.GetSection("FastApi");


builder.Services.AddScoped<IReviewerService, ReviewerService>();

var connectionString = Environment.GetEnvironmentVariable("ConnectionStrings__DefaultConnection")
                       ?? builder.Configuration.GetConnectionString("DefaultConnection");

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

builder.Services.AddHttpClient<IGithubAuthService, GitHubAuthService>();
builder.Services.AddScoped<IGithubAuthService, GitHubAuthService>();

builder.Services.AddHttpClient<IJiraService, JiraService>();
builder.Services.AddScoped<IJiraService, JiraService>(); 

builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();
builder.Services.AddScoped(typeof(IGenericRepository<AuthUser, Guid>), typeof(GenericRepository<AuthUser, Guid>));

builder.Services.AddHttpClient("FastApiClient", client =>
{
    client.BaseAddress = new Uri("http://127.0.0.1:8000/");
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

builder.Services.AddScoped<IRiskService, RiskService>();
builder.Services.AddScoped<CsvProcessor>();
builder.Services.AddScoped<IReviewerService, ReviewerService>();

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});
builder.Services.AddHttpClient("ReviewerApiClient", client =>
    {
        client.BaseAddress = new Uri("http://127.0.0.1:8000/"); 
        client.DefaultRequestHeaders.Add("Accept", "application/json");
    
    });

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

app.UseCors("AllowAll");
app.UseHttpsRedirection();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
    app.UseSwagger();
    app.UseSwaggerUI();
}

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