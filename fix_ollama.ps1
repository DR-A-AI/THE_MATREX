[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0", "Machine")
New-NetFirewallRule -DisplayName "Allow Ollama WSL" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
Write-Host "Ollama is now configured and restarted."
Start-Sleep -Seconds 3
