Set WshShell = Wscript.CreateObject("Wscript.Shell")
Dim regCmd: regCmd = "%SystemRoot%\\System32\\reg.exe DELETE ""HKLM\SOFTWARE\Policies\Microsoft\Windows Defender"" /v DisableAntiSpyware /f"
Wscript.Echo regCmd
WshShell.Run(regCmd)
Wscript.Sleep 5000
Dim netCmd: netCmd = "%SystemRoot%\\System32\\net.exe start windefend"
Wscript.Echo netCmd
WshShell.Run(netCmd)
Wscript.Sleep 5000
WshShell.Run """%PROGRAMFILES%\Windows Defender\MSASCui.exe""", 9
Wscript.Sleep 5000
WshShell.SendKeys "%{C}"
Wscript.Sleep 5000
WshShell.SendKeys "%{F4}"
Wscript.Sleep 5000
WshShell.Run """%PROGRAMFILES%\Windows Defender\MSASCui.exe""", 9
Wscript.Sleep 5000
WshShell.SendKeys "{ENTER}"

