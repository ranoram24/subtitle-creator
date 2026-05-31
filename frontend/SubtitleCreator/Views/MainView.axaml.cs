using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using SubtitleCreator.ViewModels;

namespace SubtitleCreator.Views;

public partial class MainView : UserControl
{
    public MainView() => InitializeComponent();

    private async void OnBrowseClicked(object? sender, RoutedEventArgs e)
    {
        var topLevel = TopLevel.GetTopLevel(this);
        if (topLevel is null) return;

        var files = await topLevel.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Select a video file",
            AllowMultiple = false,
            FileTypeFilter =
            [
                new FilePickerFileType("Video files")
                {
                    Patterns = ["*.mp4", "*.mkv", "*.avi", "*.mov", "*.m4v", "*.wmv", "*.flv"]
                },
                FilePickerFileTypes.All
            ]
        });

        if (files.Count == 1 && DataContext is MainViewModel vm)
            vm.SelectedFilePath = files[0].TryGetLocalPath();
    }
}
