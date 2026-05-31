using System.Collections.ObjectModel;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubtitleCreator.Models;
using SubtitleCreator.Services;

namespace SubtitleCreator.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly PythonBridgeService _bridge;

    public ObservableCollection<JobViewModel> Jobs { get; } = [];

    [ObservableProperty] private PipelineType _selectedPipeline = PipelineType.HebToHeb;
    [ObservableProperty] private string? _selectedFilePath;
    [ObservableProperty] private JobViewModel? _activeJob;

    public MainViewModel(PythonBridgeService bridge)
    {
        _bridge = bridge;
        _ = ListenToMessagesAsync();
    }

    [RelayCommand]
    private void StartJob()
    {
        if (string.IsNullOrWhiteSpace(SelectedFilePath)) return;

        var job = new SubtitleJob
        {
            VideoPath = SelectedFilePath,
            Pipeline = SelectedPipeline,
        };
        var vm = new JobViewModel(job.Id, job.VideoPath, job.Pipeline);
        Jobs.Add(vm);
        ActiveJob = vm;

        _bridge.SendStartJob(job.Id, job.VideoPath, job.Pipeline);
    }

    [RelayCommand]
    private void CancelJob(JobViewModel? vm)
    {
        if (vm is null) return;
        _bridge.SendCancelJob(vm.JobId);
        vm.Status = JobStatus.Cancelled;
        vm.Stage = "Cancelled";
    }

    private async Task ListenToMessagesAsync()
    {
        await foreach (var msg in _bridge.Messages.ReadAllAsync())
        {
            var vm = Jobs.FirstOrDefault(j => j.JobId == msg.JobId);
            if (vm is null) continue;

            await Dispatcher.UIThread.InvokeAsync(() =>
            {
                switch (msg)
                {
                    case PythonBridgeService.ProgressMessage p:
                        vm.ApplyProgress(p.Stage, p.Percent, p.ElapsedS);
                        break;
                    case PythonBridgeService.SegmentMessage s:
                        vm.ApplySegment(new SubtitleSegment(s.Index, s.Start, s.End, s.Text));
                        break;
                    case PythonBridgeService.CompleteMessage c:
                        vm.ApplyComplete(c.SrtPath, c.SegmentCount);
                        break;
                    case PythonBridgeService.ErrorMessage e:
                        vm.ApplyError(e.Message, e.Recoverable);
                        break;
                }
            });
        }
    }
}
