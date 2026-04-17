@echo off

echo Checking if Ollama is already running...

netstat -ano | findstr :11434 > nul
if %errorlevel%==0 (
    echo Ollama is already running.
) else (
    echo Starting Ollama...
    start "" /B ollama serve

    echo Waiting for Ollama to start...
    timeout /t 8 > nul
)

echo Loading model gemma4:31b (warmup)...
ollama run gemma4:31b "hello" > nul

echo Running main.py script...
"D:\Coding\Python\AINewsAnchor\.venv\Scripts\python.exe" "D:\Coding\Python\AINewsAnchor\main.py"

echo Stopping Ollama (optional)...

REM Only kill if you want to stop it every time
REM taskkill /IM ollama.exe /F

echo Done!
pause