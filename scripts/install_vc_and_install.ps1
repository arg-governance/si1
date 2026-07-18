$paths = @( 
 'C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat',
 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat',
 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat',
 'C:\Program Files (x86)\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Output "Sourcing $p"
        & "$p"
        C:/Users/Timm/AppData/Local/Python/bin/python.exe -m pip install --upgrade pip setuptools wheel
        C:/Users/Timm/AppData/Local/Python/bin/python.exe -m pip install llama-cpp-python sentencepiece huggingface_hub transformers
        exit 0
    }
}
$vswhere='C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path $vswhere) {
    $inst = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($inst) {
        $vc = Join-Path $inst 'VC\Auxiliary\Build\vcvars64.bat'
        if (Test-Path $vc) {
            Write-Output "Sourcing $vc"
            & "$vc"
            C:/Users/Timm/AppData/Local/Python/bin/python.exe -m pip install --upgrade pip setuptools wheel
            C:/Users/Timm/AppData/Local/Python/bin/python.exe -m pip install llama-cpp-python sentencepiece huggingface_hub transformers
            exit 0
        }
    }
}
Write-Error 'vcvars64.bat not found; please open the x64 Native Tools Command Prompt and retry.'
exit 1
