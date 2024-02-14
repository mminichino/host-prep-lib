#
#
Set-StrictMode -Off

function Test-CommandAvailable {
    param (
        [Parameter(Mandatory = $True, Position = 0)]
        [String] $Command
    )
    return [Boolean](Get-Command $Command -ErrorAction SilentlyContinue)
}

if (!(Test-CommandAvailable('scoop')))
{
    echo "Installing Scoop package manager"
    iex "& {$( irm get.scoop.sh )} -RunAsAdmin"
} else {
    echo "Scoop package manager already installed"
}

echo "Installing base software packages"
try
{
    Stop-Transcript | out-null
}
catch [System.InvalidOperationException]{}
Start-Transcript -path $env:Temp\bootstrap_log.txt -append

scoop bucket add versions
scoop install python311 -g
scoop install git openssl cmake make jq -g
scoop bucket add java
scoop install maven microsoft11-jdk -g

Stop-Transcript
echo "Done."
