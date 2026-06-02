using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubtitleCreator.Models;
using SubtitleCreator.Services;

namespace SubtitleCreator.ViewModels;

public partial class MainViewModel : ObservableObject
{
    private readonly PythonBridgeService _bridge;
    private readonly AppSettings _settings;

    [ObservableProperty] private string? _selectedFilePath;
    [ObservableProperty] private JobViewModel? _currentJob;
    [ObservableProperty] private string? _warningMessage;

    public MainViewModel(PythonBridgeService bridge, AppSettings settings)
    {
        _bridge = bridge;
        _settings = settings;

        if (!bridge.IsRunning)
            WarningMessage = "Python backend not found — run scripts/setup.ps1 first.";
        else if (string.IsNullOrWhiteSpace(settings.OpenAiApiKey))
            WarningMessage = "No API key set. Go to Settings and enter your API key.";

        _ = ListenToMessagesAsync();
    }

    [RelayCommand(CanExecute = nameof(CanStart))]
    private void StartEnglish() => StartJob("english");

    [RelayCommand(CanExecute = nameof(CanStart))]
    private void StartHebrew() => StartJob("hebrew");

    private bool CanStart() => !string.IsNullOrWhiteSpace(SelectedFilePath)
                               && CurrentJob?.IsActive != true;

    partial void OnSelectedFilePathChanged(string? value)
    {
        StartEnglishCommand.NotifyCanExecuteChanged();
        StartHebrewCommand.NotifyCanExecuteChanged();
    }
    partial void OnCurrentJobChanged(JobViewModel? value)
    {
        StartEnglishCommand.NotifyCanExecuteChanged();
        StartHebrewCommand.NotifyCanExecuteChanged();
    }

    private void StartJob(string pipeline)
    {
        if (string.IsNullOrWhiteSpace(SelectedFilePath)) return;

        if (!_bridge.IsRunning)
        {
            WarningMessage = "Python backend is not running. Check the Settings tab.";
            return;
        }

        if (string.IsNullOrWhiteSpace(_settings.OpenAiApiKey))
        {
            WarningMessage = "No API key — go to Settings and enter your API key first.";
            return;
        }

        var jobId = Guid.NewGuid().ToString();
        CurrentJob = new JobViewModel(jobId, SelectedFilePath, pipeline)
        {
            CancelRequested = CancelJob,
        };

        _bridge.SendStartJob(jobId, SelectedFilePath, pipeline);
    }

    internal void CancelJob(JobViewModel vm)
    {
        vm.Status  = JobStatus.Cancelled;
        vm.Stage   = "Cancelling…";
        vm.Percent = 0;

        _bridge.CancelJob(vm.JobId);

        _ = Task.Delay(2000).ContinueWith(_ =>
            Dispatcher.UIThread.InvokeAsync(() =>
            {
                vm.Stage = "Cancelled";
                StartEnglishCommand.NotifyCanExecuteChanged();
                StartHebrewCommand.NotifyCanExecuteChanged();
            }));
    }

    private async Task ListenToMessagesAsync()
    {
        await foreach (var msg in _bridge.Messages.ReadAllAsync())
        {
            if (msg is PythonBridgeService.LogMessage log)
            {
                await Dispatcher.UIThread.InvokeAsync(() => CurrentJob?.Logs.Add(log.Text));
                continue;
            }

            var vm = CurrentJob;
            if (vm is null || vm.JobId != msg.JobId) continue;
            if (vm.Status == JobStatus.Cancelled) continue;

            await Dispatcher.UIThread.InvokeAsync(() =>
            {
                switch (msg)
                {
                    case PythonBridgeService.ProgressMessage p:
                        vm.ApplyProgress(p.Stage, p.Percent, p.ElapsedS);
                        StartEnglishCommand.NotifyCanExecuteChanged();
                        StartHebrewCommand.NotifyCanExecuteChanged();
                        break;
                    case PythonBridgeService.SegmentMessage s:
                        vm.ApplySegment(new SubtitleSegment(s.Index, s.Start, s.End, s.Text));
                        break;
                    case PythonBridgeService.CompleteMessage c:
                        vm.ApplyComplete(c.SrtPath, c.SegmentCount);
                        StartEnglishCommand.NotifyCanExecuteChanged();
                        StartHebrewCommand.NotifyCanExecuteChanged();
                        break;
                    case PythonBridgeService.ErrorMessage e:
                        vm.ApplyError(e.Message, e.Recoverable);
                        StartEnglishCommand.NotifyCanExecuteChanged();
                        StartHebrewCommand.NotifyCanExecuteChanged();
                        break;
                }
            });
        }
    }
}
