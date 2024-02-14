#
#
Set-StrictMode -Off
$LogFilePath = "$HOME\bootstrap_log.txt"

function Test-CommandAvailable {
    param (
        [Parameter(Mandatory = $True, Position = 0)]
        [String] $Command
    )
    return [Boolean](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Create-ShortCut {
    param (
        [Parameter(Mandatory = $True, Position = 0)]
        [string] $SourceExe,
        [Parameter(Mandatory = $True, Position = 1)]
        [string] $ShortcutName
    )

    $DestinationPath = "$HOME\Desktop\$ShortcutName.lnk"
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($DestinationPath)
    $Shortcut.TargetPath = $SourceExe
    $Shortcut.Save()
}

function PowerShell-Path {
    if (Test-Path -Path "$PSHOME\pwsh.exe")
    {
        $path = "$PSHOME\pwsh.exe"
    } else {
        $path = "$PSHOME\powershell.exe"
    }
    return $path
}

if (!(Test-CommandAvailable('scoop')))
{
    echo "Installing Scoop package manager"
    iex "& {$( irm get.scoop.sh )} -RunAsAdmin"
} else {
    echo "Scoop package manager already installed"
}

echo "Installing base software packages"

Invoke-Command {
    scoop bucket add versions
    scoop install python311 -g
    scoop install git openssl cmake make jq -g
    scoop bucket add java
    scoop install maven microsoft11-jdk -g
} *>&1 | Out-File -FilePath $LogFilePath -NoClobber -Append

echo "Creating shortcuts"
$PowerShellPath = PowerShell-Path
Create-ShortCut($PowerShellPath, "PowerShell")

echo "Done."
