$ErrorActionPreference = "Stop"

$settings = [ordered]@{
    LLAMACPP_KEEP_ALIVE = "-1"
    LLAMACPP_NUM_PARALLEL = "1"
    LLAMACPP_MAX_LOADED_MODELS = "2"
    LLAMACPP_FLASH_ATTENTION = "1"
    LLAMACPP_KV_CACHE_TYPE = "q8_0"
    LLAMACPP_IGPU_ENABLE = "0"
}

foreach ($name in $settings.Keys) {
    $value = $settings[$name]
    [Environment]::SetEnvironmentVariable($name, $value, "User")
    Set-Item -Path "Env:$name" -Value $value
}

Write-Host "Applied CPU cache llama.cpp profile for current user:"
foreach ($name in $settings.Keys) {
    Write-Host "  $name=$([Environment]::GetEnvironmentVariable($name, "User"))"
}
Write-Host ""
Write-Host "Restart local LLM runtime for these settings to take effect."
