@echo off
setlocal

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "RUN_B=0"
set "RUN_M=0"
set "RUN_F=0"

:loop
if "%~1"=="" goto done
if /I "%~1"=="b" set "RUN_B=1"
if /I "%~1"=="m" set "RUN_M=1"
if /I "%~1"=="f" set "RUN_F=1"
shift
goto loop

:done
if "%RUN_B%"=="1" goto run
if "%RUN_M%"=="1" goto run
if "%RUN_F%"=="1" goto run

echo ========================================================
echo Utilisation : active b m f
echo   b : Backend (FastAPI via Anaconda)
echo   m : Mobile (Flutter)
echo   f : Front (Angular)
echo ========================================================
exit /b

:run
set "CONDA_ACTIVATE="
if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE=%USERPROFILE%\anaconda3\Scripts\activate.bat"
if exist "C:\ProgramData\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE=C:\ProgramData\anaconda3\Scripts\activate.bat"
if exist "D:\Download\anaconda3\Scripts\activate.bat" set "CONDA_ACTIVATE=D:\Download\anaconda3\Scripts\activate.bat"

if "%RUN_B%"=="0" goto skip_b
echo [START] Demarrage du Backend...
if not "%CONDA_ACTIVATE%"=="" goto launch_conda_path
start "Backend FastAPI" cmd /k "conda activate ocr_hand & cd /d ""%PROJECT_DIR%"" & python ocr_handwritten.py"
goto skip_b

:launch_conda_path
start "Backend FastAPI" cmd /k "call ""%CONDA_ACTIVATE%"" ocr_hand & cd /d ""%PROJECT_DIR%"" & python ocr_handwritten.py"

:skip_b
if "%RUN_F%"=="0" goto skip_f
echo [START] Demarrage du Front Angular...
start "Front Angular" cmd /k "cd /d ""%PROJECT_DIR%front-angular"" & npm start"
:skip_f

if "%RUN_M%"=="0" goto skip_m
echo [START] Demarrage de l'App Mobile Flutter...
start "Mobile Flutter" cmd /k "cd /d ""%PROJECT_DIR%mobile"" & flutter run"
:skip_m

echo Lancement termine !