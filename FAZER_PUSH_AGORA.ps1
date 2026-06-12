# Script PowerShell para fazer PUSH do Bot-Geral
# Execute este arquivo dentro da pasta C:\Users\Roberto\bot-geral\

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         FAZENDO PUSH DO BOT-GERAL PARA GITHUB              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verificar se está na pasta correta
if (-not (Test-Path ".git")) {
    Write-Host "❌ ERRO: Este não é um repositório git!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Este script deve ser executado dentro da pasta bot-geral" -ForegroundColor Yellow
    Write-Host "(a pasta que contém .git e bot_geral.py)" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Pressione ENTER para sair"
    exit 1
}

# Mostrar status
Write-Host "Verificando status..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "Fazendo PUSH..." -ForegroundColor Yellow
Write-Host "════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Fazer push
$pushOutput = git push origin main 2>&1
$pushSuccess = $LASTEXITCODE -eq 0

Write-Host $pushOutput

if ($pushSuccess) {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║          ✅ PUSH REALIZADO COM SUCESSO!                    ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Próximos passos:" -ForegroundColor Cyan
    Write-Host "1. Vá para: https://github.com/koryyn/bot-geral" -ForegroundColor White
    Write-Host "2. Verifique que o commit foi atualizado" -ForegroundColor White
    Write-Host "3. Vá para: https://github.com/koryyn/bot-geral/actions" -ForegroundColor White
    Write-Host "4. Clique em 'Run workflow' para testar" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║              ❌ ERRO AO FAZER PUSH!                        ║" -ForegroundColor Red
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host "Verifique:" -ForegroundColor Yellow
    Write-Host "- Sua conexão com internet" -ForegroundColor White
    Write-Host "- Se suas credenciais do GitHub estão configuradas" -ForegroundColor White
    Write-Host "- Se você tem permissão de write no repositório" -ForegroundColor White
    Write-Host ""
    Read-Host "Pressione ENTER para sair"
    exit 1
}

Read-Host "Pressione ENTER para sair"
