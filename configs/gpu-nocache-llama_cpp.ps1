$ErrorActionPreference = "Stop"

$settings = [ordered]@{
    LLAMACPP_KEEP_ALIVE = "-1"
    LLAMACPP_NUM_PARALLEL = "1"
    LLAMACPP_MAX_LOADED_MODELS = "1"
    LLAMACPP_IGPU_ENABLE = "1"
}

$disabled = @(
    "LLAMACPP_FLASH_ATTENTION",
    "LLAMACPP_KV_CACHE_TYPE"
)

foreach ($name in $settings.Keys) {
    $value = $settings[$name]
    [Environment]::SetEnvironmentVariable($name, $value, "User")
    Set-Item -Path "Env:$name" -Value $value
}

foreach ($name in $disabled) {
    [Environment]::SetEnvironmentVariable($name, $null, "User")
    Set-Item -Path "Env:$name" -Value $null
}

Write-Host "Applied GPU no-cache llama.cpp profile for current user:"
foreach ($name in $settings.Keys) {
    Write-Host "  $name=$([Environment]::GetEnvironmentVariable($name, "User"))"
}
Write-Host ""
Write-Host "Restart local LLM runtime for these settings to take effect."
