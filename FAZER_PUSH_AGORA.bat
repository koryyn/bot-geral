@echo off
REM Script para fazer PUSH do Bot-Geral atualizado
REM Execute este arquivo dentro da pasta C:\Users\Roberto\bot-geral\

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         FAZENDO PUSH DO BOT-GERAL PARA GITHUB              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Verificar se está na pasta correta
if not exist ".git" (
    echo ❌ ERRO: Este não é um repositório git!
    echo.
    echo Este script deve ser executado dentro da pasta bot-geral
    echo (a pasta que contém .git e bot_geral.py)
    echo.
    pause
    exit /b 1
)

REM Mostrar status
echo Verificando status...
git status

echo.
echo ════════════════════════════════════════════════════════════
echo Fazendo PUSH...
echo ════════════════════════════════════════════════════════════
echo.

REM Fazer push
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║          ✅ PUSH REALIZADO COM SUCESSO!                    ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo Próximos passos:
    echo 1. Vá para: https://github.com/koryyn/bot-geral
    echo 2. Verifique que o commit foi atualizado
    echo 3. Vá para: https://github.com/koryyn/bot-geral/actions
    echo 4. Clique em "Run workflow" para testar
    echo.
    pause
) else (
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║              ❌ ERRO AO FAZER PUSH!                        ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo Verifique:
    echo - Sua conexão com internet
    echo - Se suas credenciais do GitHub estão configuradas
    echo - Se você tem permissão de write no repositório
    echo.
    pause
    exit /b 1
)
