@echo off
chcp 65001 >nul
title Бункер — Клиент

echo Проверка зависимостей...
python -c "import PyQt6" 2>nul || (
    echo Устанавливаю PyQt6...
    pip install PyQt6
)
python -c "import websockets" 2>nul || (
    echo Устанавливаю websockets...
    pip install websockets
)

echo Запуск игры...
python "%~dp0bunker_client.py"
pause
