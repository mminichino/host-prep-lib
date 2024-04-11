#
#
Set-StrictMode -Off
$LogFilePath = "$HOME\sqlserver_log.txt"

curl -OLs https://download.microsoft.com/download/c/c/9/cc9c6797-383c-4b24-8920-dc057c1de9d3/SQL2022-SSEI-Dev.exe --output-dir C:\Temp
curl -OLs https://download.microsoft.com/download/b/9/7/b97061b9-9b9c-4bc7-86de-22b262c016d1/SSMS-Setup-ENU.exe --output-dir C:\Temp
