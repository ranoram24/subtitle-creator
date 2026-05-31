using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using SubtitleCreator.ViewModels;

namespace SubtitleCreator.Views;

public partial class MainView : UserControl
{
    public MainView()
    {
        InitializeComponent();
        DropZone.AddHandler(DragDrop.DropEvent, OnDrop);
        DropZone.AddHandler(DragDrop.DragOverEvent, OnDragOver);
    }

    private static void OnDragOver(object? sender, DragEventArgs e)
    {
        e.DragEffects = e.DataTransfer.Contains(DataFormat.File)
            ? DragDropEffects.Copy
            : DragDropEffects.None;
    }

    private void OnDrop(object? sender, DragEventArgs e)
    {
        if (!e.DataTransfer.Contains(DataFormat.File)) return;

        var files = e.DataTransfer.TryGetFiles()?.ToList();
        if (files is null || files.Count == 0) return;

        var first = files[0].TryGetLocalPath();
        if (first is not null && DataContext is MainViewModel vm)
            vm.SelectedFilePath = first;
    }

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
                    Patterns = ["*.mp4", "*.mkv", "*.avi", "*.mov", "*.m4v", "*.wmv", "*.flv", "*.ts", "*.webm"]
                },
                FilePickerFileTypes.All
            ]
        });

        if (files.Count == 1 && DataContext is MainViewModel vm)
            vm.SelectedFilePath = files[0].TryGetLocalPath();
    }
}
