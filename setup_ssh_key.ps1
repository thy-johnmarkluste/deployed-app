# SSH Key Setup Script for Ubuntu Access
# Run this script ONCE to set up passwordless SSH authentication

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SSH Key Setup for Ubuntu Domain Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$keyPath = "$env:USERPROFILE\.ssh\ubuntu_key"
$pubKeyPath = "$keyPath.pub"
$hostname = Read-Host "Enter SSH host (IP or domain)"
$username = Read-Host "Enter SSH username"

if ([string]::IsNullOrWhiteSpace($hostname) -or [string]::IsNullOrWhiteSpace($username)) {
    Write-Host "Host and username are required." -ForegroundColor Red
    exit 1
}

# Check if SSH directory exists
if (!(Test-Path "$env:USERPROFILE\.ssh")) {
    Write-Host "Creating .ssh directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" | Out-Null
}

# Generate SSH key if it doesn't exist
if (!(Test-Path $keyPath)) {
    Write-Host "Generating SSH key pair..." -ForegroundColor Yellow
    ssh-keygen -t ed25519 -f $keyPath -N '""' -C "$env:USERNAME-windows-to-ubuntu"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ SSH key generated successfully!" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to generate SSH key" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ SSH key already exists at $keyPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Now copying public key to Ubuntu server..." -ForegroundColor Yellow
Write-Host "You will be prompted for your Ubuntu password ONE TIME." -ForegroundColor Yellow
Write-Host ""

# Copy public key to server
$pubKey = Get-Content $pubKeyPath -Raw
$sshCommand = "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

ssh "${username}@${hostname}" $sshCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now use the GUI without password prompts!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Install Python dependencies: pip install paramiko" -ForegroundColor White
    Write-Host "2. Run the GUI: python domain_connector.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Testing connection..." -ForegroundColor Yellow
    ssh -i $keyPath "${username}@${hostname}" "echo 'Connection successful!'"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Passwordless SSH is working!" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "✗ Failed to copy key to server" -ForegroundColor Red
    Write-Host "Please check your username and password, then try again." -ForegroundColor Red
}
