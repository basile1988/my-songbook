@echo off
chcp 65001 >nul
title My Songbook
cd /d "%~dp0"

if exist "%USERPROFILE%\anaconda3\python.exe" (
  "%USERPROFILE%\anaconda3\python.exe" server.py
  goto end
)
where py >nul 2>nul && (
  py -3 server.py
  goto end
)
where python >nul 2>nul && (
  python server.py
  goto end
)
echo.
echo Δεν βρέθηκε Python. Εγκατάστησέ την από https://www.python.org/downloads/
echo και ξανατρέξε αυτό το αρχείο.
:end
pause
