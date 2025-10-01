using Core.Domain.Contracts;
using Core.Domain.Models;
using Core.Services;
using Microsoft.AspNetCore.Mvc;

namespace Infrastructure.Presentation.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RiskController :ControllerBase
{
    private readonly IRiskService _riskService;
    private readonly CsvProcessor _csvProcessor;

    public RiskController(IRiskService predictionService, CsvProcessor csvProcessor)
    {
        _riskService = predictionService;
        _csvProcessor = csvProcessor;
    }

    [HttpPost]
    public async Task<IActionResult> Predict([FromBody] RiskInput input)
    {
        var result = await _riskService.GetPredictionAsync(input);
        return Ok(result);
    }

    [HttpPost("process-csv")]
    public async Task<IActionResult> ProcessCsv([FromQuery] string csvFilePath)
    {
        if (!System.IO.File.Exists(csvFilePath))
        {
            return BadRequest("CSV file not found.");
        }

        var results = await _csvProcessor.ProcessCsvAsync(csvFilePath);
        return Ok(results);
    }  
}