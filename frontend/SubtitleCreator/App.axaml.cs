using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
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
            _bridge = new PythonBridgeService();

            // Resolve python executable and backend path relative to the app executable.
            var appDir = AppContext.BaseDirectory;
            var backendDir = Path.GetFullPath(Path.Combine(appDir, "..", "..", "..", "..", "..", "backend"));
            var pythonExe = Path.Combine(backendDir, ".venv", "Scripts", "python.exe");

            if (File.Exists(pythonExe))
                _bridge.Start(pythonExe, backendDir);
            else
                System.Diagnostics.Debug.WriteLine(
                    $"[App] Python venv not found at {pythonExe} — run scripts/setup.ps1 first.");

            var vm = new MainViewModel(_bridge);
            desktop.MainWindow = new MainWindow { DataContext = vm };

            desktop.ShutdownRequested += async (_, _) => await _bridge.DisposeAsync();
        }

        base.OnFrameworkInitializationCompleted();
    }
}