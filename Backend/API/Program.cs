using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Domain.Models;
using Infrastructure.Persistence.Data;
using Infrastructure.Persistence.Repositories;
using Infrastructure.Presentation.Controllers;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();
builder.Services.AddControllers()
       .AddApplicationPart(typeof(GitHubAuthController).Assembly);


   
 builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

  
  builder.Services.AddHttpClient<IGithubAuthService, GitHubAuthService>();
  builder.Services.AddScoped<IUnitOfWork, UnitOfWork>();
  builder.Services.AddScoped(typeof(IGenericRepository<AuthUser,Guid>), typeof(GenericRepository<AuthUser,Guid>));





var app = builder.Build();

app.UseHttpsRedirection();
app.MapControllers();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();


app.Run();

