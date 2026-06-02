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
    public record LogMessage(string Text)
        : IpcMessage("log", "");

    private readonly Channel<IpcMessage> _channel =
        Channel.CreateUnbounded<IpcMessage>(new UnboundedChannelOptions { SingleWriter = true });

    public ChannelReader<IpcMessage> Messages => _channel.Reader;

    private Process? _process;
    private string? _pythonExe;
    private string? _backendDir;

    public bool IsRunning => _process is { HasExited: false };

    public void Start(string pythonExe, string backendDir)
    {
        _pythonExe = pythonExe;
        _backendDir = backendDir;
        _StartProcess();
    }

    private void _StartProcess()
    {
        if (_pythonExe is null || _backendDir is null) return;

        var logPath = Path.Combine(Path.GetTempPath(), "subtitle-creator-backend.log");

        var psi = new ProcessStartInfo
        {
            FileName = _pythonExe,
            Arguments = $"-u \"{Path.Combine(_backendDir, "main.py")}\"",
            WorkingDirectory = _backendDir,
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardInputEncoding = new System.Text.UTF8Encoding(encoderShouldEmitUTF8Identifier: false),
        };
        psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

        File.WriteAllText(logPath, $"[{DateTime.Now:HH:mm:ss}] Starting backend: {_pythonExe}\n");

        _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _process.OutputDataReceived += OnOutput;
        _process.ErrorDataReceived += OnStderr;
        _process.Start();
        _process.StandardInput.AutoFlush = true;   // without this, writes sit in the StreamWriter buffer forever
        _process.BeginOutputReadLine();
        _process.BeginErrorReadLine();
    }

    public void SendStartJob(string jobId, string videoPath, string pipeline = "english", string? outputDir = null)
    {
        if (!IsRunning) return;
        var json = JsonSerializer.Serialize(new
        {
            type = "start_job",
            job_id = jobId,
            video_path = videoPath,
            pipeline,
            output_dir = outputDir ?? string.Empty,
        });
        _process!.StandardInput.WriteLine(json);
    }

    /// <summary>
    /// Cancel a job.  If the job is loading a model, the gentle signal has no
    /// effect — so after a short grace period we hard-kill the Python process
    /// and restart it so the UI is responsive again.
    /// </summary>
    public void CancelJob(string jobId)
    {
        // Gentle signal first
        if (IsRunning)
        {
            try
            {
                var json = JsonSerializer.Serialize(new { type = "cancel_job", job_id = jobId });
                _process!.StandardInput.WriteLine(json);
            }
            catch { /* stdin may already be closed */ }
        }

        // Hard-kill after 1.5 s — the only reliable way to interrupt model loading
        _ = Task.Run(async () =>
        {
            await Task.Delay(1500);
            ForceKillAndRestart();
        });
    }

    public void ForceKillAndRestart()
    {
        if (_process is not null)
        {
            try
            {
                if (!_process.HasExited) _process.Kill(entireProcessTree: true);
            }
            catch { }
            _process.Dispose();
            _process = null;
        }
        _StartProcess();
    }

    public void SendShutdown()
    {
        if (!IsRunning) return;
        try
        {
            var json = JsonSerializer.Serialize(new { type = "shutdown" });
            _process!.StandardInput.WriteLine(json);
        }
        catch { }
    }

    private void OnOutput(object sender, DataReceivedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(e.Data)) return;
        try
        {
            var node = JsonNode.Parse(e.Data);
            if (node is null) return;
            var type  = node["type"]?.GetValue<string>()  ?? "";
            var jobId = node["job_id"]?.GetValue<string>() ?? "";

            IpcMessage msg = type switch
            {
                "progress" => new ProgressMessage(
                    jobId,
                    node["stage"]?.GetValue<string>()        ?? "",
                    node["percent"]?.GetValue<int>()         ?? 0,
                    node["elapsed_s"]?.GetValue<double?>()),
                "segment" => new SegmentMessage(
                    jobId,
                    node["index"]?.GetValue<int>()           ?? 0,
                    node["start"]?.GetValue<double>()        ?? 0,
                    node["end"]?.GetValue<double>()          ?? 0,
                    node["text"]?.GetValue<string>()         ?? ""),
                "complete" => new CompleteMessage(
                    jobId,
                    node["srt_path"]?.GetValue<string>()     ?? "",
                    node["segment_count"]?.GetValue<int>()   ?? 0),
                "error" => new ErrorMessage(
                    jobId,
                    node["message"]?.GetValue<string>()      ?? "",
                    node["recoverable"]?.GetValue<bool>()    ?? false),
                _ => new IpcMessage(type, jobId),
            };

            _channel.Writer.TryWrite(msg);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[bridge] parse error: {ex.Message} | raw: {e.Data}");
        }
    }

    private void OnStderr(object sender, DataReceivedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(e.Data)) return;
        Debug.WriteLine($"[python stderr] {e.Data}");
        _channel.Writer.TryWrite(new LogMessage(e.Data));
        try
        {
            var logPath = Path.Combine(Path.GetTempPath(), "subtitle-creator-backend.log");
            File.AppendAllText(logPath, $"[{DateTime.Now:HH:mm:ss}] {e.Data}\n");
        }
        catch { }
    }

    public async ValueTask DisposeAsync()
    {
        SendShutdown();
        _channel.Writer.TryComplete();
        if (_process is not null)
        {
            await Task.Run(() => _process.WaitForExit(5000));
            if (!_process.HasExited) _process.Kill(entireProcessTree: true);
            _process.Dispose();
        }
    }
}
