Invoke-WebRequest "https://github.com/3proxy/3proxy/releases/download/0.9.4/3proxy-0.9.4.win64.zip" -OutFile "C:\3proxy.zip"
Expand-Archive "C:\3proxy.zip" -DestinationPath "C:\3proxy" -Force
$exe = (Get-ChildItem "C:\3proxy" -Recurse -Filter "3proxy.exe").FullName
Set-Content "C:\3proxy\3proxy.cfg" "nserver 8.8.8.8`nnscache 65536`nauth none`nallow *`nproxy -p3128"
New-NetFirewallRule -DisplayName "3proxy" -Direction Inbound -Protocol TCP -LocalPort 3128 -Action Allow -ErrorAction SilentlyContinue
sc.exe create 3proxy binPath= "$exe C:\3proxy\3proxy.cfg" start= auto
sc.exe start 3proxy
Write-Host "Proxy instalado y corriendo en puerto 3128" -ForegroundColor Green
