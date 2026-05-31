using SubtitleCreator.Models;

namespace SubtitleCreator.Services;

public static class SrtExportService
{
    private static string Timestamp(double seconds)
    {
        var ts = TimeSpan.FromSeconds(seconds);
        return $"{(int)ts.TotalHours:D2}:{ts.Minutes:D2}:{ts.Seconds:D2},{ts.Milliseconds:D3}";
    }

    public static async Task WriteAsync(IEnumerable<SubtitleSegment> segments, string outputPath)
    {
        var lines = segments.Select(s =>
            $"{s.Index}\n{Timestamp(s.Start)} --> {Timestamp(s.End)}\n{s.Text.Trim()}\n");

        await File.WriteAllTextAsync(outputPath, string.Join("\n", lines), System.Text.Encoding.UTF8);
    }

    public static string DefaultPathFor(string videoPath)
    {
        var dir = Path.GetDirectoryName(videoPath) ?? ".";
        var name = Path.GetFileNameWithoutExtension(videoPath);
        return Path.Combine(dir, name + ".srt");
    }
}
