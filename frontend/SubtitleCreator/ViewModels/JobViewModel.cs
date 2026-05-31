using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubtitleCreator.Models;

namespace SubtitleCreator.ViewModels;

public partial class JobViewModel : ObservableObject
{
    public string JobId { get; }
    public string VideoFileName { get; }
    public PipelineType Pipeline { get; }

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(IsRunning))]
    [NotifyPropertyChangedFor(nameof(IsActive))]
    private JobStatus _status = JobStatus.Pending;

    [ObservableProperty] private int _percent;
    [ObservableProperty] private string _stage = "Queued";
    [ObservableProperty] private double _elapsedSeconds;
    [ObservableProperty] private string? _srtPath;
    [ObservableProperty] private string? _errorMessage;

    public bool IsRunning => Status == JobStatus.Running;
    public bool IsActive  => Status is JobStatus.Pending or JobStatus.Running;

    public ObservableCollection<SubtitleSegment> Segments { get; } = [];

    public Action<JobViewModel>? CancelRequested { get; set; }

    public JobViewModel(string jobId, string videoPath, PipelineType pipeline)
    {
        JobId = jobId;
        VideoFileName = Path.GetFileName(videoPath);
        Pipeline = pipeline;
    }

    [RelayCommand]
    private void Cancel() => CancelRequested?.Invoke(this);

    public void ApplyProgress(string stage, int percent, double? elapsedS)
    {
        Stage = stage switch
        {
            "extracting_audio" => "Extracting audio…",
            "loading_model"    => "Loading AI model… (first run may take several minutes)",
            "transcribing"     => "Transcribing…",
            "translating"      => "Translating to Hebrew…",
            "writing_srt"      => "Writing SRT…",
            _ => stage,
        };
        Percent = percent;
        if (elapsedS.HasValue) ElapsedSeconds = elapsedS.Value;
        Status = JobStatus.Running;
    }

    public void ApplySegment(SubtitleSegment seg) => Segments.Add(seg);

    public void ApplyComplete(string srtPath, int count)
    {
        SrtPath = srtPath;
        Stage = $"Done — {count} subtitles";
        Percent = 100;
        Status = JobStatus.Completed;
    }

    public void ApplyError(string message, bool recoverable)
    {
        ErrorMessage = message;
        if (!recoverable)
            Status = JobStatus.Failed;
    }
}
