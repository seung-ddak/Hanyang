param([switch]$Uninstall, [switch]$CheckOnly, [switch]$NoLaunch)
$ErrorActionPreference = 'Stop'
$marker = 'Hanyang CS interview study widget (quad-study-widget-v1)'
$startupPath = [Environment]::GetFolderPath('Startup')
if (-not $startupPath) { throw 'Cannot resolve the current user Startup folder.' }
$startupPath = [IO.Path]::GetFullPath($startupPath)
$shortcutPath = Join-Path $startupPath 'Hanyang-CS-Study-Widget.lnk'
if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($shortcutPath)) -ne $startupPath) { throw 'Invalid startup shortcut path.' }
$widgetPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'study_widget.pyw'))
$pythonCommand = Get-Command pythonw.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pythonCommand -and -not $Uninstall) { throw 'pythonw.exe was not found. Install Python with tkinter first.' }
$arguments = '"{0}"' -f $widgetPath
$exists = Test-Path -LiteralPath $shortcutPath -PathType Leaf
$shell = New-Object -ComObject WScript.Shell
if ($exists) {
    $existing = $shell.CreateShortcut($shortcutPath)
    if ($existing.Description -ne $marker -or $existing.Arguments -ne $arguments) {
        throw "A different shortcut already occupies this name. No changes made: $shortcutPath"
    }
}
if ($CheckOnly) {
    [pscustomobject]@{ Action = $(if ($Uninstall) {'Uninstall'} else {'Install'}); Shortcut = $shortcutPath; Exists = $exists; Widget = $widgetPath; Python = $(if ($pythonCommand) {$pythonCommand.Source} else {''}) }
    exit 0
}
if ($Uninstall) {
    if ($exists) {
        Remove-Item -LiteralPath $shortcutPath
        Write-Output "Removed only the login shortcut. Reinstall to restore it: $shortcutPath"
    } else { Write-Output 'The login shortcut was not installed.' }
    Write-Output 'Study files, settings, and progress were preserved. Close any running widget separately.'
    exit 0
}
if (-not (Test-Path -LiteralPath $widgetPath -PathType Leaf)) { throw "Missing widget: $widgetPath" }
if (-not (Test-Path -LiteralPath $startupPath -PathType Container)) { throw "Startup folder does not exist: $startupPath" }
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonCommand.Source
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = $marker
$shortcut.WindowStyle = 1
$shortcut.IconLocation = "$($pythonCommand.Source),0"
$shortcut.Save()
$verify = $shell.CreateShortcut($shortcutPath)
if ($verify.TargetPath -ne $pythonCommand.Source -or $verify.Arguments -ne $arguments -or $verify.Description -ne $marker) {
    throw 'Shortcut verification failed.'
}
Write-Output "Installed current-user login shortcut: $shortcutPath"
if (-not $NoLaunch) {
    Start-Process -FilePath $pythonCommand.Source -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Normal
    Write-Output 'Opened the study widget.'
}
