# Creates a "QuantOS" shortcut on the Desktop that launches the app
# windowless (server in background, Edge app window in front).
# Run once: .\tools\create_desktop_shortcut.ps1

$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop "QuantOS.lnk"))
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -WindowStyle Hidden -Command `"& '$projectDir\venv\Scripts\python.exe' '$projectDir\tools\desktop_app.py'`""
$shortcut.WorkingDirectory = $projectDir
$shortcut.Description = "QuantOS Desktop - trading operator console"
$shortcut.Save()
Write-Host "Desktop shortcut created: $desktop\QuantOS.lnk"
