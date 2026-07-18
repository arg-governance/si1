@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\vsdevcmd\ext\vcvars.bat" x64
C:\Users\Timm\AppData\Local\Python\bin\python.exe -m pip install --upgrade pip setuptools wheel
C:\Users\Timm\AppData\Local\Python\bin\python.exe -m pip install llama-cpp-python sentencepiece huggingface_hub transformers
C:\Users\Timm\AppData\Local\Python\bin\python.exe -c "from llama_cpp import Llama; print('LLAMA_IMPORT_OK')"
PAUSE
