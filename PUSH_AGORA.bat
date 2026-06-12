@echo off
REM Script para fazer push do bot-geral atualizado

cd /d C:\Users\Roberto\bot-geral

echo Limpando lock file...
del /F /Q .git\index.lock 2>nul

echo.
echo Adicionando arquivo...
git add bot_geral.py

echo.
echo Fazendo commit...
git commit -m "Fix: Reescrever fazer_login com descoberta dinamica de campos - Coleta TODOS os campos hidden - Detecta campos dinamicamente - Inclui ID do formulario no payload"

echo.
echo Fazendo PUSH...
git push origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo ✅ SUCESSO!
    echo.
    echo Verifique em: https://github.com/koryyn/bot-geral/commits/main
) else (
    echo ❌ Erro ao fazer push
)

pause
