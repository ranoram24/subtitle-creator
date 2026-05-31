namespace SubtitleCreator.Services;

/// <summary>
/// Locates the Python backend directory and venv executable by walking up
/// from the application's base directory until a "backend/" folder is found.
/// Works for both Debug (deep in bin/Debug/net9.0/) and published layouts.
/// </summary>
public static class BackendLocator
{
    public record Location(string BackendDir, string PythonExe);

    /// <summary>
    /// Returns the resolved location, or null if neither the venv nor a
    /// system Python can be found alongside a backend/ directory.
    /// </summary>
    public static Location? Find()
    {
        var backendDir = FindBackendDir(AppContext.BaseDirectory);
        if (backendDir is null) return null;

        // Prefer the project-local venv
        var venvPython = Path.Combine(backendDir, ".venv", "Scripts", "python.exe");
        if (File.Exists(venvPython))
            return new Location(backendDir, venvPython);

        // Fall back to whatever python is on PATH
        var systemPython = FindOnPath("python.exe") ?? FindOnPath("python3.exe");
        if (systemPython is not null)
            return new Location(backendDir, systemPython);

        return null;
    }

    private static string? FindBackendDir(string startDir)
    {
        var dir = new DirectoryInfo(startDir);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "backend");
            if (Directory.Exists(candidate) &&
                File.Exists(Path.Combine(candidate, "main.py")))
                return candidate;
            dir = dir.Parent;
        }
        return null;
    }

    private static string? FindOnPath(string exeName)
    {
        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (var dir in pathEnv.Split(Path.PathSeparator))
        {
            var full = Path.Combine(dir.Trim(), exeName);
            if (File.Exists(full)) return full;
        }
        return null;
    }
}
