using SubtitleCreator.Models;
using SubtitleCreator.Services;

namespace SubtitleCreator.ViewModels;

public class MainWindowViewModel
{
    public MainViewModel Main { get; }
    public SettingsViewModel Settings { get; }

    public MainWindowViewModel(PythonBridgeService bridge, AppSettings settings)
    {
        Main     = new MainViewModel(bridge, settings);
        Settings = new SettingsViewModel(settings);
    }
}
