#
#
Set-StrictMode -Off
$LogFilePath = "$HOME\devserver_log.txt"

scoop bucket add extras
scoop install aws -g
scoop install gcloud -g
scoop install azure-cli -g
scoop install python38 -g
scoop install python311 -g
scoop reset python312
python -m pip install --upgrade pip
pip install poetry
pip install tox
