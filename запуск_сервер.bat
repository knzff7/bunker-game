@echo off
chcp 65001 >nul
title Бункер — Сервер (Локальный)

python -c "import websockets" 2>nul || (
    echo Устанавливаю websockets...
    pip install websockets
)

echo Сервер запущен на порту 8765
echo Для остановки нажмите Ctrl+C
python "%~dp0server.py"
pause
