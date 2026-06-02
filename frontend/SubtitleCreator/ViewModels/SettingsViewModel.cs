using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubtitleCreator.Models;

namespace SubtitleCreator.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly AppSettings _settings;

    [ObservableProperty] private string _openAiApiKey;
    [ObservableProperty] private string _pythonExeOverride;
    [ObservableProperty] private string _statusMessage = string.Empty;

    public SettingsViewModel(AppSettings settings)
    {
        _settings = settings;
        _openAiApiKey     = settings.OpenAiApiKey     ?? string.Empty;
        _pythonExeOverride = settings.PythonExeOverride ?? string.Empty;
    }

    [RelayCommand]
    private void Save()
    {
        _settings.OpenAiApiKey      = string.IsNullOrWhiteSpace(OpenAiApiKey)      ? null : OpenAiApiKey;
        _settings.PythonExeOverride  = string.IsNullOrWhiteSpace(PythonExeOverride)  ? null : PythonExeOverride;
        _settings.Save();
        StatusMessage = "Saved. Restart the app to apply a new API key.";
    }
}
