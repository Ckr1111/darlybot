@echo off
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

if not exist dist mkdir dist

pyinstaller --onefile --name RofeBotDJMaxBridge --paths src src\rofebot_bridge\__main__.py
