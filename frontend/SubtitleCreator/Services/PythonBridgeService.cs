using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Channels;
using SubtitleCreator.Models;

namespace SubtitleCreator.Services;

/// <summary>
/// Spawns the Python backend process and exposes a channel of strongly-typed IPC messages.
/// </summary>
public sealed class PythonBridgeService : IAsyncDisposable
{
    public record IpcMessage(string Type, string JobId);
    public record ProgressMessage(string JobId, string Stage, int Percent, double? ElapsedS)
        : IpcMessage("progress", JobId);
    public record SegmentMessage(string JobId, int Index, double Start, double End, string Text)
        : IpcMessage("segment", JobId);
    public record CompleteMessage(string JobId, string SrtPath, int SegmentCount)
        : IpcMessage("complete", JobId);
    public record ErrorMessage(string JobId, string Message, bool Recoverable)
        : IpcMessage("error", JobId);

    private readonly Channel<IpcMessage> _channel =
        Channel.CreateUnbounded<IpcMessage>(new UnboundedChannelOptions { SingleWriter = true });

    public ChannelReader<IpcMessage> Messages => _channel.Reader;

    private Process? _process;

    /// <summary>Starts the Python backend subprocess.</summary>
    public void Start(string pythonExe, string backendDir)
    {
        var psi = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = $"\"{Path.Combine(backendDir, "main.py")}\"",
            WorkingDirectory = backendDir,
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardInputEncoding = System.Text.Encoding.UTF8,
        };

        _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _process.OutputDataReceived += OnOutput;
        _process.ErrorDataReceived += OnStderr;
        _process.Start();
        _process.BeginOutputReadLine();
        _process.BeginErrorReadLine();
    }

    public void SendStartJob(string jobId, string videoPath, PipelineType pipeline)
    {
        var pipelineStr = pipeline == PipelineType.HebToHeb ? "heb_to_heb" : "any_to_heb";
        var json = JsonSerializer.Serialize(new
        {
            type = "start_job",
            job_id = jobId,
            video_path = videoPath,
            pipeline = pipelineStr,
        });
        _process?.StandardInput.WriteLine(json);
    }

    public void SendCancelJob(string jobId)
    {
        var json = JsonSerializer.Serialize(new { type = "cancel_job", job_id = jobId });
        _process?.StandardInput.WriteLine(json);
    }

    public void SendShutdown()
    {
        var json = JsonSerializer.Serialize(new { type = "shutdown" });
        _process?.StandardInput.WriteLine(json);
    }

    private void OnOutput(object sender, DataReceivedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(e.Data)) return;
        try
        {
            var node = JsonNode.Parse(e.Data);
            if (node is null) return;
            var type = node["type"]?.GetValue<string>() ?? "";
            var jobId = node["job_id"]?.GetValue<string>() ?? "";

            IpcMessage msg = type switch
            {
                "progress" => new ProgressMessage(
                    jobId,
                    node["stage"]?.GetValue<string>() ?? "",
                    node["percent"]?.GetValue<int>() ?? 0,
                    node["elapsed_s"]?.GetValue<double>()),
                "segment" => new SegmentMessage(
                    jobId,
                    node["index"]?.GetValue<int>() ?? 0,
                    node["start"]?.GetValue<double>() ?? 0,
                    node["end"]?.GetValue<double>() ?? 0,
                    node["text"]?.GetValue<string>() ?? ""),
                "complete" => new CompleteMessage(
                    jobId,
                    node["srt_path"]?.GetValue<string>() ?? "",
                    node["segment_count"]?.GetValue<int>() ?? 0),
                "error" => new ErrorMessage(
                    jobId,
                    node["message"]?.GetValue<string>() ?? "",
                    node["recoverable"]?.GetValue<bool>() ?? false),
                _ => new IpcMessage(type, jobId),
            };

            _channel.Writer.TryWrite(msg);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[bridge] parse error: {ex.Message} | raw: {e.Data}");
        }
    }

    private static void OnStderr(object sender, DataReceivedEventArgs e)
    {
        if (!string.IsNullOrWhiteSpace(e.Data))
            Debug.WriteLine($"[python stderr] {e.Data}");
    }

    public async ValueTask DisposeAsync()
    {
        SendShutdown();
        _channel.Writer.TryComplete();
        if (_process is not null)
        {
            await Task.Run(() => _process.WaitForExit(5000));
            if (!_process.HasExited)
                _process.Kill();
            _process.Dispose();
        }
    }
}
