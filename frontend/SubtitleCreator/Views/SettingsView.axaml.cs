using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using SubtitleCreator.ViewModels;

namespace SubtitleCreator.Views;

public partial class SettingsView : UserControl
{
    public SettingsView() => InitializeComponent();

    private async void OnBrowseOutputDirClicked(object? sender, RoutedEventArgs e)
    {
        var tl = TopLevel.GetTopLevel(this);
        if (tl is null) return;

        var folders = await tl.StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
        {
            Title = "Select output folder",
            AllowMultiple = false,
        });

        if (folders.Count == 1 && DataContext is SettingsViewModel vm)
            vm.OutputDirectory = folders[0].Path.LocalPath;
    }
}
