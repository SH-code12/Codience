using System;
using Core.Domain.Models;
using System.Linq.Expressions;
using System.Threading;
using System.Threading.Tasks;
using System.Net.Http;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Core.Abstraction;
using Core.Domain.Contracts;
using Core.Services;
using Microsoft.Extensions.Configuration;
using Moq;
using Moq.Protected;
using Xunit;

namespace Tests;

public class JiraServiceTests
{
    private readonly Mock<IUnitOfWork> _uowMock;
    private readonly Mock<IConfiguration> _configMock;
    private readonly Mock<HttpMessageHandler> _handlerMock;
    private readonly JiraService _service;

    public JiraServiceTests()
    {
        _uowMock = new Mock<IUnitOfWork>();
        _configMock = new Mock<IConfiguration>();
        _handlerMock = new Mock<HttpMessageHandler>();
        var httpClient = new HttpClient(_handlerMock.Object);
        _service = new JiraService(httpClient, _configMock.Object, _uowMock.Object);
    }

    [Fact]
    public async Task GetAccessibleResources_ReturnsJsonElement()
    {
        // Arrange
        var expectedJson = "[{\"id\": \"123\", \"name\": \"Site\"}]";
        _handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(expectedJson)
            });

        // Act
        var result = await _service.GetAccessibleResources("fake_token");

        // Assert
        Assert.Equal(JsonValueKind.Array, result.ValueKind);
        Assert.Equal("123", result[0].GetProperty("id").GetString());
    }

    [Fact]
    public async Task AssignIssueAsync_ReturnsTrueOnSuccess()
    {
        // Arrange
        _handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.NoContent
            });

        // Act
        var result = await _service.AssignIssueAsync("fake_token", "cloud_id", "issue_key", "account_id");

        // Assert
        Assert.True(result);
    }

    [Fact]
    public async Task GetAllProjects_ReturnsProjects()
    {
        // Arrange
        var expectedJson = "[{\"id\": \"10000\", \"key\": \"PROJ\"}]";
        _handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(expectedJson)
            });

        // Act
        var result = await _service.GetAllProjects("fake_token", "cloud_id");

        // Assert
        Assert.Equal(JsonValueKind.Array, result.ValueKind);
        Assert.Equal("PROJ", result[0].GetProperty("key").GetString());
    }

    [Fact]
    public async Task GetIssues_ReturnsIssues()
    {
        // Arrange
        var expectedJson = "{\"issues\": [{\"key\": \"ISSUE-1\"}]}";
        _handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(expectedJson)
            });

        // Act
        var result = await _service.GetIssues("fake_token", "cloud_id", "PROJ");

        // Assert
        Assert.Equal(JsonValueKind.Object, result.ValueKind);
        Assert.True(result.TryGetProperty("issues", out var issues));
        Assert.Equal("ISSUE-1", issues[0].GetProperty("key").GetString());
    }

    [Fact]
    public async Task GetProjectRoles_ReturnsRoles()
    {
        // Arrange
        var expectedJson = "{\"Administrator\": \"https://...\" }";
        _handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(expectedJson)
            });

        // Act
        var result = await _service.GetProjectRoles("fake_token", "cloud_id", "PROJ");

        // Assert
        Assert.Equal(JsonValueKind.Object, result.ValueKind);
        Assert.True(result.TryGetProperty("Administrator", out _));
    }

    [Fact]
    public async Task ExchangeCodeForAdminToken_ReturnsToken()
    {
        // Arrange
        var expectedJson = "{\"access_token\": \"real_token\" }";
        _handlerMock.Protected()
            .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
            .ReturnsAsync(new HttpResponseMessage
            {
                StatusCode = HttpStatusCode.OK,
                Content = new StringContent(expectedJson)
            });

        _configMock.Setup(c => c["Jira:ClientId"]).Returns("client_id");
        _configMock.Setup(c => c["Jira:ClientSecret"]).Returns("secret");
        _configMock.Setup(c => c["Jira:CallbackUrl"]).Returns("callback");

        // Act
        var result = await _service.ExchangeCodeForAdminToken("code");

        // Assert
        Assert.Equal("real_token", result);
    }

    [Fact]
    public async Task SaveJiraIssuesAsync_SavesIssuesToDb()
    {
        // Arrange
        var issuesJson = JsonDocument.Parse("{\"issues\": [{\"key\": \"ISSUE-1\", \"fields\": {\"summary\": \"Test Sum\", \"status\": {\"name\": \"Open\"}, \"issuetype\": {\"name\": \"Task\"}}}] }").RootElement;
        var user = new AuthUser { Id = Guid.NewGuid(), AuthUserName = "testuser" };

        var userRepoMock = new Mock<IGenericRepository<AuthUser, Guid>>();
        userRepoMock.Setup(r => r.FirstOrDefaultAsync(It.IsAny<Expression<Func<AuthUser, bool>>>()))
            .ReturnsAsync(user);

        var issueRepoMock = new Mock<IGenericRepository<JiraIssue, int>>();
        
        _uowMock.Setup(u => u.GetGenericRepository<AuthUser, Guid>()).Returns(userRepoMock.Object);
        _uowMock.Setup(u => u.GetGenericRepository<JiraIssue, int>()).Returns(issueRepoMock.Object);

        // Act
        await _service.SaveJiraIssuesAsync("testuser", "cloud_id", "PROJ", issuesJson);

        // Assert
        issueRepoMock.Verify(r => r.AddAsync(It.Is<JiraIssue>(i => i.JiraKey == "ISSUE-1" && i.UserId == user.Id)), Times.Once);
        _uowMock.Verify(u => u.SaveChangesAsync(), Times.Once);
    }
}
