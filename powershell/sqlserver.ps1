#
#
Set-StrictMode -Off
$LogFilePath = "$HOME\sqlserver_log.txt"

function Create-ShortCut {
    param (
        [Parameter(Mandatory = $True, Position = 0)]
        [string] $SourceExe,
        [Parameter(Mandatory = $True, Position = 1)]
        [string] $ShortcutName
    )

    $DestinationPath = "$HOME\Desktop\$ShortcutName.lnk"
    if (Test-Path -Path $DestinationPath) {
        return
    }
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($DestinationPath)
    $Shortcut.TargetPath = $SourceExe
    $Shortcut.Save()
}

curl -OLs https://download.microsoft.com/download/c/c/9/cc9c6797-383c-4b24-8920-dc057c1de9d3/SQL2022-SSEI-Dev.exe --output-dir C:\Temp
curl -OLs https://download.microsoft.com/download/b/9/7/b97061b9-9b9c-4bc7-86de-22b262c016d1/SSMS-Setup-ENU.exe --output-dir C:\Temp
curl -OLs https://raw.githubusercontent.com/couchbaselabs/host-prep-lib/main/powershell/SQLServerInstall.ini --output-dir C:\Temp

Get-Disk | Where-Object {$_.PartitionStyle -eq ‘Raw’} | Initialize-Disk -PartitionStyle GPT
New-Partition -DiskNumber 2 -DriveLetter E -UseMaximumSize
Format-Volume -DriveLetter E -FileSystem NTFS

C:\Temp\SQL2022-SSEI-Dev.exe /QUIET /ACTION=Download /MEDIAPATH=C:\Temp

#C:\Temp\SQLServer2022-DEV-x64-ENU.exe /x:C:\Temp\SQLServer /ConfigurationFile=C\Temp\SQLServerInstall.ini
#C:\Temp\SSMS-Setup-ENU.exe /Install /Passive /SSMSInstallRoot="C:\Program Files (x86)\Microsoft SQL Server Management Studio 20"

#Create-ShortCut "C:\Windows\SysWOW64\mmc.exe /32 C:\Windows\SysWOW64\SQLServerManager16.msc" "SQL Server Config"
#Create-ShortCut "C:\Program Files (x86)\Microsoft SQL Server Management Studio 20\Common7\IDE\Ssms.exe" "SQL Server Management"
