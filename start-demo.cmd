@echo off
cd /d "%~dp0"
where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo Node.js and npm are required. Install Node.js, then try again.
  pause
  exit /b 1
)
if not exist node_modules (
  call npm.cmd ci
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
echo Blue demo: http://127.0.0.1:4319/?v=blue
echo Green demo: http://127.0.0.1:4319/?v=green
echo Keep this window open while previewing.
call npm.cmd run dev
pause
