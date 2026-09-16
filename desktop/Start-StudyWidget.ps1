param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$widgetPath = Join-Path $PSScriptRoot 'study_widget.pyw'
$pythonCommand = Get-Command pythonw.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pythonCommand) { throw 'pythonw.exe was not found. Install Python with tkinter, then try again.' }
$pythonPath = $pythonCommand.Source
if (-not (Test-Path -LiteralPath $widgetPath -PathType Leaf)) { throw "Missing widget: $widgetPath" }
if ($CheckOnly) {
    [pscustomobject]@{ Python = $pythonPath; Widget = $widgetPath; WorkingDirectory = $PSScriptRoot }
    exit 0
}
Start-Process -FilePath $pythonPath -ArgumentList ('"{0}"' -f $widgetPath) -WorkingDirectory $PSScriptRoot -WindowStyle Normal
