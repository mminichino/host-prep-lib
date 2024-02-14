#
#
echo "Installing Scoop package manager"
iex "& {$(irm get.scoop.sh)} -RunAsAdmin"

echo "Installing base software packages"
Stop-Transcript | out-null
Start-Transcript -path $env:Temp\bootstrap_log.txt -append

scoop bucket add versions
scoop install python311 -g
scoop install git openssl cmake make jq -g
scoop bucket add java
scoop install maven microsoft11-jdk -g

Stop-Transcript
echo "Done."
