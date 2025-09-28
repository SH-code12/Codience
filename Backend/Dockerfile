# ===== Base image =====
FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080

# ===== Build stage =====
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy all project files and folders
COPY API/ API/
COPY Core/ Core/
COPY Infrastructure/ Infrastructure/
COPY Solution.Core.sln .

# Restore dependencies for the API project
RUN dotnet restore "API/Codience.API.csproj"

# Copy all other source code (if any new files)
COPY . .

# Publish the API
WORKDIR "/src/API"
RUN dotnet publish "Codience.API.csproj" -c Release -o /app/publish

# ===== Final stage =====
FROM base AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "Codience.API.dll"]
