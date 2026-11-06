@echo off
setlocal
set RUN_B=0
:loop
if "%~1"=="" goto done
if /I "%~1"=="b" set RUN_B=1
shift
goto loop
:done
echo %RUN_B%