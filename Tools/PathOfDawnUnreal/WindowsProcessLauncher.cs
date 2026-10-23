// Host tooling only, loaded by PowerShell Add-Type. Not an Unreal runtime module.
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace PathOfDawn.Tools
{
    public static class WindowsProcessLauncher
    {
        [StructLayout(LayoutKind.Sequential)]
        private struct SecurityAttributes
        {
            public int Length;
            public IntPtr SecurityDescriptor;
            [MarshalAs(UnmanagedType.Bool)] public bool InheritHandle;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct StartupInfo
        {
            public int Size;
            public IntPtr Reserved, Desktop, Title;
            public uint X, Y, XSize, YSize, XCountChars, YCountChars, FillAttribute, Flags;
            public ushort ShowWindow, ReservedSize;
            public IntPtr ReservedBytes, StdInput, StdOutput, StdError;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct StartupInfoEx
        {
            public StartupInfo Info;
            public IntPtr AttributeList;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct ProcessInformation
        {
            public IntPtr Process, Thread;
            public uint ProcessId, ThreadId;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, ExactSpelling = true)]
        private static extern SafeFileHandle CreateFileW(string name, uint access, uint share,
            ref SecurityAttributes security, uint disposition, uint flags, IntPtr template);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, uint flags, ref IntPtr size);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, IntPtr attribute,
            IntPtr value, IntPtr size, IntPtr previousValue, IntPtr returnSize);

        [DllImport("kernel32.dll")]
        private static extern void DeleteProcThreadAttributeList(IntPtr list);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true, ExactSpelling = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CreateProcessW(string application, StringBuilder commandLine,
            IntPtr processAttributes, IntPtr threadAttributes, [MarshalAs(UnmanagedType.Bool)] bool inheritHandles,
            uint flags, IntPtr environment, string directory, ref StartupInfoEx startup, out ProcessInformation process);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern uint ResumeThread(IntPtr thread);

        [DllImport("kernel32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool TerminateProcess(IntPtr process, uint exitCode);

        [DllImport("kernel32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool CloseHandle(IntPtr handle);

        private static SafeFileHandle OpenHandle(string path, uint access, uint disposition)
        {
            var security = new SecurityAttributes {
                Length = Marshal.SizeOf<SecurityAttributes>(), InheritHandle = true
            };
            // Logs can be read while the game is running. CREATE_NEW protects
            // existing files; Common.ps1 supplies unique log names per process.
            var handle = CreateFileW(path, access, 3, ref security, disposition, 0x80, IntPtr.Zero);
            if (handle.IsInvalid)
            {
                int error = Marshal.GetLastWin32Error();
                handle.Dispose();
                throw new Win32Exception(error, "Cannot open process stream: " + path);
            }
            return handle;
        }

        public static Process Start(string file, string commandLine, string directory,
            string stdoutPath, string stderrPath, bool hidden)
        {
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                throw new PlatformNotSupportedException("The native handle-list launcher requires Windows.");

            using (var input = OpenHandle("NUL", 0x80000000, 3)) // GENERIC_READ, OPEN_EXISTING
            using (var output = OpenHandle(stdoutPath, 0x40000000, 1)) // GENERIC_WRITE, CREATE_NEW
            using (var error = OpenHandle(stderrPath, 0x40000000, 1))
            {
                IntPtr list = IntPtr.Zero, handles = IntPtr.Zero, size = IntPtr.Zero;
                bool initialized = false;
                var native = new ProcessInformation();
                Process process = null;
                try
                {
                    // The sizing call is documented to fail with ERROR_INSUFFICIENT_BUFFER.
                    InitializeProcThreadAttributeList(IntPtr.Zero, 1, 0, ref size);
                    if (size == IntPtr.Zero)
                        throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot size the process handle list.");
                    list = Marshal.AllocHGlobal(size);
                    if (!InitializeProcThreadAttributeList(list, 1, 0, ref size))
                        throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot initialize the process handle list.");
                    initialized = true;
                    handles = Marshal.AllocHGlobal(3 * IntPtr.Size);
                    Marshal.WriteIntPtr(handles, 0, input.DangerousGetHandle());
                    Marshal.WriteIntPtr(handles, IntPtr.Size, output.DangerousGetHandle());
                    Marshal.WriteIntPtr(handles, 2 * IntPtr.Size, error.DangerousGetHandle());
                    // PROC_THREAD_ATTRIBUTE_HANDLE_LIST: inherit ONLY these three
                    // handles. Redirecting stdio alone still leaks other ancestor
                    // pipeline handles with PowerShell's Start-Process on Windows.
                    if (!UpdateProcThreadAttribute(list, 0, new IntPtr(0x00020002), handles,
                        new IntPtr(3 * IntPtr.Size), IntPtr.Zero, IntPtr.Zero))
                        throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot restrict inherited process handles.");
                    var startup = new StartupInfoEx {
                        Info = new StartupInfo {
                            Size = Marshal.SizeOf<StartupInfoEx>(), Flags = 0x101, // USESTDHANDLES | USESHOWWINDOW
                            ShowWindow = (ushort)(hidden ? 0 : 1),
                            StdInput = input.DangerousGetHandle(), StdOutput = output.DangerousGetHandle(),
                            StdError = error.DangerousGetHandle()
                        },
                        AttributeList = list
                    };
                    // EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED. A hidden
                    // console worker gets CREATE_NO_WINDOW; a local GUI is shown.
                    uint flags = 0x00080000 | 0x00000004 | (hidden ? 0x08000000u : 0x00000010u);
                    if (!CreateProcessW(file, new StringBuilder(commandLine), IntPtr.Zero, IntPtr.Zero,
                        true, flags, IntPtr.Zero, directory, ref startup, out native))
                        throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot start: " + file);
                    process = Process.GetProcessById((int)native.ProcessId);
                    // Acquire our own handle before resuming even a short-lived child.
                    var ownedHandle = process.Handle;
                    if (ResumeThread(native.Thread) == uint.MaxValue)
                        throw new Win32Exception(Marshal.GetLastWin32Error(), "Cannot resume: " + file);
                    return process;
                }
                catch
                {
                    if (native.Process != IntPtr.Zero) TerminateProcess(native.Process, 1);
                    if (process != null) process.Dispose();
                    throw;
                }
                finally
                {
                    if (native.Thread != IntPtr.Zero) CloseHandle(native.Thread);
                    if (native.Process != IntPtr.Zero) CloseHandle(native.Process);
                    if (initialized) DeleteProcThreadAttributeList(list);
                    if (list != IntPtr.Zero) Marshal.FreeHGlobal(list);
                    if (handles != IntPtr.Zero) Marshal.FreeHGlobal(handles);
                }
            }
        }
    }
}
