# ========================
# Base runtime image
# ========================
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080

# ========================
# Build stage
# ========================
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy solution
COPY Codience.sln .

# Copy project files ONLY (for restore caching)
COPY API/Codience.API.csproj API/
COPY Core/Abstraction/Core.Abstraction.csproj Core/Abstraction/
COPY Core/Domain/Core.Domain.csproj Core/Domain/
COPY Core/Services/Core.Services.csproj Core/Services/
COPY Infrastructure/Persistence/Infrastructure.Persistence.csproj Infrastructure/Persistence/
COPY Infrastructure/Presentation/Infrastructure.Presentation.csproj Infrastructure/Presentation/
COPY Share/Share.csproj Share/

# Restore dependencies
RUN dotnet restore API/Codience.API.csproj

# Now copy everything
COPY . .

# Publish
WORKDIR /src/API
RUN dotnet publish Codience.API.csproj -c Release -o /app/publish --no-restore

# ========================
# Final image
# ========================
FROM base AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "Codience.API.dll"]
