#
#
Set-StrictMode -Off
$LogFilePath = "$HOME\devserver_log.txt"

scoop bucket add extras
scoop install aws -g
scoop install gcloud -g
scoop install azure-cli -g
