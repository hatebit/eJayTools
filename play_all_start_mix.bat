@echo off
REM Play all START.MIX files for each disk using apps/emp/src/mixplayer.py
REM This script renders 8 bars from bar 82 (or bar 1 for section formats) to WAV files

set PYTHON=python
set PLAYER=apps/emp/src/mixplayer.py

echo ========================================
echo Playing all START.MIX files
echo ========================================

REM Dance eJay 1.x (grid format, 0-based bars)
echo.
echo [1/6] Dance eJay 1.x
%PYTHON% %PLAYER% disks/Dance_eJay/MIX/START.MIX
if %ERRORLEVEL% NEQ 0 echo Failed: Dance_eJay

REM Rave eJay 1.x (grid format, 0-based bars)
echo.
echo [2/6] Rave eJay 1.x
%PYTHON% %PLAYER% disks/Rave_eJay/MIX/START.MIX
if %ERRORLEVEL% NEQ 0 echo Failed: Rave_eJay

REM HipHop eJay 1.x (grid format, 0-based bars)
echo.
echo [3/6] HipHop eJay 1.x
%PYTHON% %PLAYER% disks/Hiphop_eJay/MIX/START.MIX
if %ERRORLEVEL% NEQ 0 echo Failed: Hiphop_eJay

REM Dance eJay 2 (section format, 1-based bars)
echo.
echo [4/6] Dance eJay 2
%PYTHON% %PLAYER% disks/Dance_2/MIX/START.MIX --format dance2
if %ERRORLEVEL% NEQ 0 echo Failed: Dance_2

REM Techno eJay 2 (section format, 1-based bars)
echo.
echo [5/6] Techno eJay 2
%PYTHON% %PLAYER% disks/Techno_eJay/MIX/START.MIX --format techno
if %ERRORLEVEL% NEQ 0 echo Failed: Techno_eJay

REM Dance eJay NRG (grid format, 0-based bars - extra disk)
echo.
echo [6/6] Dance eJay NRG
%PYTHON% %PLAYER% disks/Dance_eJay_NRG/MIX/START.MIX
if %ERRORLEVEL% NEQ 0 echo Failed: Dance_eJay_NRG

echo.
echo ========================================
echo Done!
echo ========================================
