param(
    [string]$Target = "build"
)

switch ($Target) {
    "dev"   { docker compose up --build }
    "test"  { docker run --rm nirikshan pytest -q }
    "build" { docker build -t nirikshan . }
    "lint"  { Set-Location frontend; cmd /c "npm run build"; Set-Location .. }
    default { Write-Host "Unknown target: $Target. Available: dev, test, build, lint" }
}
