using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using SubtitleCreator.Models;

namespace SubtitleCreator.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly AppSettings _settings;

    [ObservableProperty] private string _selectedTheme;
    [ObservableProperty] private string _outputDirectory;
    [ObservableProperty] private string _statusMessage = string.Empty;

    public static string[] ThemeOptions { get; } = ["System default", "Light", "Dark"];

    public SettingsViewModel(AppSettings settings)
    {
        _settings = settings;
        _selectedTheme   = settings.Theme switch { "Light" => "Light", "Dark" => "Dark", _ => "System default" };
        _outputDirectory = settings.OutputDirectoryOverride ?? string.Empty;
    }

    partial void OnSelectedThemeChanged(string value)
    {
        App.ApplyTheme(value == "Light" ? "Light" : value == "Dark" ? "Dark" : "Default");
    }

    [RelayCommand]
    private void Save()
    {
        _settings.Theme                  = SelectedTheme == "Light" ? "Light" : SelectedTheme == "Dark" ? "Dark" : "Default";
        _settings.OutputDirectoryOverride = string.IsNullOrWhiteSpace(OutputDirectory) ? null : OutputDirectory;
        _settings.Save();
        StatusMessage = "Saved.";
    }
}
