using System.Collections.Specialized;
using System.Diagnostics;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using SubtitleCreator.ViewModels;

namespace SubtitleCreator.Views;

public partial class JobView : UserControl
{
    private INotifyCollectionChanged? _subscribedCollection;

    public JobView()
    {
        InitializeComponent();
        DataContextChanged += OnDataContextChanged;
    }

    private void OnDataContextChanged(object? sender, EventArgs e)
    {
        if (_subscribedCollection is not null)
        {
            _subscribedCollection.CollectionChanged -= OnSegmentsChanged;
            _subscribedCollection = null;
        }

        if (DataContext is JobViewModel vm)
        {
            _subscribedCollection = vm.Segments;
            vm.Segments.CollectionChanged += OnSegmentsChanged;
            vm.Logs.CollectionChanged += OnLogsChanged;
        }
    }

    private void OnSegmentsChanged(object? sender, NotifyCollectionChangedEventArgs e)
        => SegmentScroller.ScrollToEnd();

    private void OnLogsChanged(object? sender, NotifyCollectionChangedEventArgs e)
        => LogScroller.ScrollToEnd();

    private void OnSrtPathClicked(object? sender, PointerPressedEventArgs e)
    {
        if (DataContext is JobViewModel vm && vm.SrtPath is { } path)
        {
            // Open the containing folder with the file highlighted
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = "explorer.exe",
                    Arguments = $"/select,\"{path}\"",
                    UseShellExecute = true,
                });
            }
            catch { /* non-critical */ }
        }
    }
}
