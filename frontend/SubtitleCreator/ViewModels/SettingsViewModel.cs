using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubtitleCreator.Models;

namespace SubtitleCreator.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly AppSettings _settings;

    [ObservableProperty] private string _pythonExeOverride;
    [ObservableProperty] private string _outputDirectoryOverride;
    [ObservableProperty] private string _preferredDevice;
    [ObservableProperty] private string _statusMessage = string.Empty;

    public IReadOnlyList<string> DeviceOptions { get; } = ["auto", "cuda", "cpu"];

    public SettingsViewModel(AppSettings settings)
    {
        _settings = settings;
        _pythonExeOverride      = settings.PythonExeOverride ?? string.Empty;
        _outputDirectoryOverride = settings.OutputDirectoryOverride ?? string.Empty;
        _preferredDevice        = settings.PreferredDevice;
    }

    [RelayCommand]
    private void Save()
    {
        _settings.PythonExeOverride       = string.IsNullOrWhiteSpace(PythonExeOverride)  ? null : PythonExeOverride;
        _settings.OutputDirectoryOverride = string.IsNullOrWhiteSpace(OutputDirectoryOverride) ? null : OutputDirectoryOverride;
        _settings.PreferredDevice         = PreferredDevice;
        _settings.Save();
        StatusMessage = "Settings saved.";
    }

    [RelayCommand]
    private void Reset()
    {
        PythonExeOverride       = string.Empty;
        OutputDirectoryOverride = string.Empty;
        PreferredDevice         = "auto";
        StatusMessage = string.Empty;
    }
}
