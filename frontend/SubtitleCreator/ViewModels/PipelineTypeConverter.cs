using System.Globalization;
using Avalonia.Data.Converters;
using SubtitleCreator.Models;

namespace SubtitleCreator.ViewModels;

/// <summary>
/// Converts between PipelineType enum and bool for RadioButton IsChecked bindings.
/// ConverterParameter is the string name of the enum value.
/// </summary>
public sealed class PipelineTypeConverter : IValueConverter
{
    public static readonly PipelineTypeConverter Instance = new();

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is PipelineType actual && parameter is string expected)
            return actual.ToString() == expected;
        return false;
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is true && parameter is string name &&
            Enum.TryParse<PipelineType>(name, out var result))
            return result;
        return Avalonia.Data.BindingOperations.DoNothing;
    }
}
