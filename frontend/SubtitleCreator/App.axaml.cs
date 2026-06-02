using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using Avalonia.Styling;
using SubtitleCreator.Models;
using SubtitleCreator.Services;
using SubtitleCreator.ViewModels;

namespace SubtitleCreator;

public partial class App : Application
{
    private PythonBridgeService? _bridge;

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var settings = AppSettings.Load();
            _bridge = new PythonBridgeService();

            ApplyTheme(settings.Theme);

            var location = BackendLocator.Find();
            if (location is not null)
            {
                var pythonExe = !string.IsNullOrWhiteSpace(settings.PythonExeOverride) &&
                                File.Exists(settings.PythonExeOverride)
                    ? settings.PythonExeOverride
                    : location.PythonExe;

                _bridge.Start(pythonExe, location.BackendDir);
            }
            else
            {
                System.Diagnostics.Debug.WriteLine(
                    "[App] Could not locate backend/ or Python — run scripts/setup.ps1 first.");
            }

            var vm = new MainWindowViewModel(_bridge, settings);
            desktop.MainWindow = new MainWindow { DataContext = vm };
            desktop.ShutdownRequested += async (_, _) => await _bridge.DisposeAsync();
        }

        base.OnFrameworkInitializationCompleted();
    }

    public static void ApplyTheme(string theme)
    {
        if (Current is null) return;
        Current.RequestedThemeVariant = theme switch
        {
            "Light" => ThemeVariant.Light,
            "Dark"  => ThemeVariant.Dark,
            _       => ThemeVariant.Default,
        };
    }
}
