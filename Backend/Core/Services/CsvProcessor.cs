using System.Globalization;
using System.Text;
using Core.Domain.Contracts;
using Core.Domain.Models;
using CsvHelper;
using CsvHelper.Configuration;

namespace Core.Services;

public class CsvProcessor
{
    private readonly IRiskService _predictionService;

    public CsvProcessor(IRiskService predictionService)
    {
        _predictionService = predictionService ?? throw new ArgumentNullException(nameof(predictionService));
    }

    public async Task<List<(string Repo, string Prediction, double Score)>> ProcessCsvAsync(string csvFilePath)
    {
        if (!File.Exists(csvFilePath))
        {
            throw new FileNotFoundException("CSV file not found.", csvFilePath);
        }

        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            Delimiter = ",",
            Quote = '"',
            Escape = '"',
            BadDataFound = context => Console.WriteLine($"Bad CSV data at row {context.Field}: {context.RawRecord}")
        };

        var results = new List<(string Repo, string Prediction, double Score)>();

        try
        {
            using var reader = new StreamReader(csvFilePath, Encoding.UTF8, true);
            using var csv = new CsvReader(reader, config);

            await csv.ReadAsync();
            csv.ReadHeader();

            while (await csv.ReadAsync())
            {
                var input = new RiskInput
                {
                    Repo = csv.GetField("repo") ?? string.Empty,
                    ProblemStatement = csv.GetField("problem_statement") ?? string.Empty,
                    Patch = csv.GetField("patch") ?? string.Empty
                };

                // Truncate to avoid overwhelming the model
                if (input.ProblemStatement.Length > 2000)
                    input.ProblemStatement = input.ProblemStatement.Substring(0, 2000) + "...";
                if (input.Patch.Length > 10000)
                    input.Patch = input.Patch.Substring(0, 10000) + "...";

                try
                {
                    var result = await _predictionService.GetPredictionAsync(input);
                    results.Add((input.Repo, result.Prediction, result.Score));
                    Console.WriteLine($"Repo: {input.Repo}, Prediction: {result.Prediction}, Score: {result.Score}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing row for repo {input.Repo}: {ex.Message}");
                }
            }
        }
        catch (Exception ex)
        {
            throw new Exception($"Failed to process CSV file: {ex.Message}", ex);
        }

        return results;
    }
}