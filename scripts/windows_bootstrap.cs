// Windowless release entry. The embedded console game starts only inside its
// configured terminal; the bootstrap itself never creates a terminal window.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

// 版本资源：build.py 在生成 DreamBootstrap.cs 时替换 @VERSION@（四段）与 @SEMVER@（pyproject 版本）。
// 交付给玩家的 exe 就是这个 csc 产物，所以版本必须写在这里，而不是只写进 PyInstaller 的核心。
[assembly: AssemblyTitle("梦层 / Oneirscript")]
[assembly: AssemblyProduct("梦层 / Oneirscript")]
[assembly: AssemblyCompany("dis5mZl1e")]
[assembly: AssemblyDescription("梦层 / Oneirscript 无窗口启动器")]
[assembly: AssemblyCopyright("GPL-3.0-only; 完整许可见随包 LICENSE")]
[assembly: AssemblyVersion("@VERSION@")]
[assembly: AssemblyFileVersion("@VERSION@")]
[assembly: AssemblyInformationalVersion("@SEMVER@")]

internal static class DreamBootstrap
{
    private const string ProfileGuid = "{cb2ca4ca-e2c0-59fd-a2c5-3d5f11980f3e}";
    private const string CoreHash = "@CORE_HASH@";
    private const long CoreSize = @CORE_SIZE@L;

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AttachConsole(uint processId);

    // Windows command-line quoting, including trailing backslashes and quotes.
    private static string Quote(string value)
    {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char character in value)
        {
            if (character == '\\') { slashes++; continue; }
            result.Append('\\', character == '"' ? slashes * 2 + 1 : slashes);
            result.Append(character);
            slashes = 0;
        }
        result.Append('\\', slashes * 2);
        return result.Append('"').ToString();
    }

    private static string Arguments(IEnumerable<string> values)
    {
        var quoted = new List<string>();
        foreach (string value in values) quoted.Add(Quote(value));
        return String.Join(" ", quoted.ToArray());
    }

    private static bool ValidCore(string path)
    {
        if (!File.Exists(path) || new FileInfo(path).Length != CoreSize) return false;
        using (var file = File.OpenRead(path))
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "") == CoreHash;
    }

    private static string PrepareCore()
    {
        string directory = Path.Combine(Environment.GetFolderPath(
            Environment.SpecialFolder.LocalApplicationData), "Oneirscript", "runtime", CoreHash);
        Directory.CreateDirectory(directory);
        string target = Path.Combine(directory, "OneirscriptCore.exe");
        if (ValidCore(target)) return target;
        string temporary = target + "." + Process.GetCurrentProcess().Id + ".tmp";
        try
        {
            using (var input = Assembly.GetExecutingAssembly().GetManifestResourceStream("OneirscriptCore"))
            using (var output = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                if (input == null) throw new IOException("游戏核心未包含在启动器中。");
                input.CopyTo(output);
                output.Flush(true);
            }
            if (!ValidCore(temporary)) throw new IOException("游戏核心校验失败，请重新打包。");
            if (File.Exists(target))
            {
                if (ValidCore(target)) return target; // Another launch finished first.
                File.Replace(temporary, target, null);
            }
            else
            {
                try { File.Move(temporary, target); }
                catch (IOException) { if (!ValidCore(target)) throw; }
            }
            return target;
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    private static void InstallProfile(string core, string root)
    {
        string face = "NSimSun";
        using (var fonts = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Fonts"))
            if (fonts != null && fonts.GetValue("Dream Strata Serif Mono (TrueType)") != null)
                face = "Dream Strata Serif Mono, NSimSun";
        var profile = new Dictionary<string, object> {
            {"guid", ProfileGuid}, {"name", "Oneirscript Serif"},
            {"commandline", Arguments(new[] {core, "--terminal-attached", "--game-directory", root})},
            {"startingDirectory", root},
            {"font", new Dictionary<string, object> {
                {"face", face}, {"size", 14}, {"weight", "normal"},
                {"cellWidth", face == "NSimSun" ? "0.6" : "0.5"},
                {"cellHeight", face == "NSimSun" ? "1.2" : "1.0"}, {"colorGlyphs", false}}},
            {"background", "#101018"}, {"antialiasingMode", "grayscale"},
            {"closeOnExit", "graceful"}, {"hidden", false}, {"suppressApplicationTitle", false}
        };
        string fragments = Path.Combine(Environment.GetFolderPath(
            Environment.SpecialFolder.LocalApplicationData), "Microsoft", "Windows Terminal", "Fragments");
        string directory = Path.Combine(fragments, "Oneirscript");
        Directory.CreateDirectory(directory);
        try { string legacy = Path.Combine(fragments, "DreamStrata"); if (Directory.Exists(legacy)) Directory.Delete(legacy, true); }
        catch { }
        string path = Path.Combine(directory, "profile.json");
        string payload = new JavaScriptSerializer().Serialize(
            new Dictionary<string, object> {{"profiles", new[] {profile}}}) + "\n";
        if (File.Exists(path) && File.ReadAllText(path, Encoding.UTF8) == payload) return;
        string temporary = path + "." + Process.GetCurrentProcess().Id + ".tmp";
        try
        {
            File.WriteAllText(temporary, payload, new UTF8Encoding(false));
            if (File.Exists(path)) File.Replace(temporary, path, null);
            else
            {
                try { File.Move(temporary, path); }
                catch (IOException) { File.Replace(temporary, path, null); }
            }
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    private static string FindTerminal()
    {
        string alias = Path.Combine(Environment.GetFolderPath(
            Environment.SpecialFolder.LocalApplicationData), "Microsoft", "WindowsApps", "wt.exe");
        if (File.Exists(alias)) return alias;
        foreach (string directory in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            if (String.IsNullOrWhiteSpace(directory)) continue;
            string candidate = Path.Combine(directory.Trim().Trim('"'), "wt.exe");
            if (File.Exists(candidate)) return candidate;
        }
        return null;
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool smoke = Array.IndexOf(args, "--smoke") >= 0;
        string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        try
        {
            string core = PrepareCore();
            var command = new List<string> {core, "--terminal-attached", "--game-directory", root};
            command.AddRange(args);
            if (smoke)
            {
                // Preserve noninteractive release checks without a visible window.
                AttachConsole(0xffffffff);
                var info = new ProcessStartInfo(core, Arguments(command.GetRange(1, command.Count - 1))) {
                    UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = root,
                    RedirectStandardOutput = true, RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8
                };
                using (var process = Process.Start(info))
                {
                    var stdout = process.StandardOutput.ReadToEndAsync();
                    var stderr = process.StandardError.ReadToEndAsync();
                    process.WaitForExit();
                    Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) {AutoFlush = true});
                    Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) {AutoFlush = true});
                    Console.Out.Write(stdout.Result);
                    Console.Error.Write(stderr.Result);
                    return process.ExitCode;
                }
            }
            if (Array.IndexOf(args, "--compat-terminal") >= 0)
            {
                // A console caller keeps its own terminal. Explorer callers get
                // one ordinary console; compatibility never redirects to WT.
                AttachConsole(0xffffffff);
                using (var process = Process.Start(new ProcessStartInfo(core,
                    Arguments(command.GetRange(1, command.Count - 1))) {
                    UseShellExecute = false, WorkingDirectory = root}))
                {
                    process.WaitForExit();
                    return process.ExitCode;
                }
            }
            // Probe and prepare fonts without creating a temporary console window.
            // The Python core starts the private WezTerm directly, or returns 2
            // for this existing Windows Terminal / ordinary console fallback.
            var prepareArgs = new List<string> {"--prepare-terminal", "--game-directory", root};
            prepareArgs.AddRange(args);
            using (var prepared = Process.Start(new ProcessStartInfo(core, Arguments(prepareArgs)) {
                UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = root}))
            {
                prepared.WaitForExit();
                if (prepared.ExitCode == 0) return 0;
            }
            string terminal = FindTerminal();
            if (terminal != null)
            {
                // Profile registration is optional. A full/read-only user
                // volume must not abort an otherwise usable game core.
                try { InstallProfile(core, root); }
                catch (IOException) { terminal = null; }
                catch (UnauthorizedAccessException) { terminal = null; }
            }
            if (terminal != null)
            {
                var terminalArgs = new List<string> {
                    "-w", "new", "new-tab", "--inheritEnvironment", "-p", ProfileGuid, "-d", root};
                terminalArgs.AddRange(command);
                using (var process = Process.Start(new ProcessStartInfo(terminal, Arguments(terminalArgs)) {
                    UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = root}))
                {
                    process.WaitForExit();
                    if (process.ExitCode == 0) return 0;
                }
            }
            // No Terminal / failed handoff: create a single ordinary console.
            Process.Start(new ProcessStartInfo(core, Arguments(command.GetRange(1, command.Count - 1))) {
                UseShellExecute = false, WorkingDirectory = root});
            return 0;
        }
        catch (Exception error)
        {
            try
            {
                string directory = Path.Combine(root, "crash_reports");
                Directory.CreateDirectory(directory);
                File.WriteAllText(Path.Combine(directory, "bootstrap_" + DateTime.Now.ToString("yyyyMMdd_HHmmss")
                    + "_" + Process.GetCurrentProcess().Id + ".log"), error.ToString(), Encoding.UTF8);
            }
            catch { }
            if (!smoke) MessageBox.Show("游戏启动失败：" + error.Message, "梦层", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
