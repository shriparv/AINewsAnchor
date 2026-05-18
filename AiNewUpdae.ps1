cd D:\Coding\Python\AINewsAnchor

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

$totalIterations = 5

for ($i = 0; $i -lt $totalIterations; $i++) {

    Write-Host "========== Iteration $($i + 1) of $totalIterations ==========" -ForegroundColor Cyan

    Write-Host "Running main.py with -n 5..." -ForegroundColor Yellow
    python .\main.py -n 5

    Write-Host "Waiting 5 minutes..." -ForegroundColor Green
    Start-Sleep -Seconds 300

    Write-Host "Running main.py with -n 10..." -ForegroundColor Yellow
    python .\main.py -n 10

    Write-Host "Waiting 5 minutes..." -ForegroundColor Green
    Start-Sleep -Seconds 300
}

Write-Host "All iterations completed." -ForegroundColor Magenta