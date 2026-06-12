# BOT-GERAL

Automação completa de pesquisa e inscrição de voluntários SEAPE.

## ⚡ Funcionalidades

- **19:58 BRT** — Pesquisa voluntários vagos disponíveis
- **19:59:50-20:00:40 BRT** — Inscrição automática em TODAS as vagas (50 segundos)
- 📲 Notificações via Telegram (opcional)
- ⏰ Executa automaticamente todos os dias via GitHub Actions

## 🚀 Quick Start

### 1. Configurar Secrets
Settings → Secrets and variables → Actions

```
SISVEP_MATRICULA = sua matrícula
SISVEP_SENHA = sua senha
TG_TOKEN = (opcional) token Telegram
TG_CHAT_ID = (opcional) seu chat ID
```

### 2. Workflow Automático
O GitHub Actions executa automaticamente:
- Diariamente às 19:58 → Pesquisa
- Diariamente às 19:59:50 → Inscrição

### 3. Monitoramento
Veja logs em: **Actions** → **BOT-GERAL - Pesquisa e Inscrição Automática**

## 🧪 Teste Manual

**Actions** → **Run workflow** → escolha `pesquisa` ou `inscricao`

## 📋 Requisitos

- Python 3.11+
- Acesso ao portal SEAPE (matrícula + senha)
- Telegram (opcional, para notificações)

## 📧 Cronograma

| Horário | Ação | Duração |
|---------|------|---------|
| 19:58 BRT | Pesquisa vagas | Instantâneo |
| 19:59:50 BRT | Inscrição contínua | 50 segundos |

## ⚙️ Estrutura

```
.github/workflows/bot-geral.yml  → Workflow GitHub Actions
bot_geral.py                      → Script principal
```

## 🔧 Personalização

Edite `bot_geral.py` para:
- Filtrar vagas por atividade/horário
- Ajustar tempo de espera
- Modificar critério de "vago"

## 📚 Documentação Completa

Veja [BOT-GERAL_SETUP.md](BOT-GERAL_SETUP.md) para instruções detalhadas.

## 📊 Logs

```bash
# Exemplo de log
[2026-06-12 19:58:00] ✓ Login realizado com sucesso
[2026-06-12 19:58:05] ✓ Encontradas 3 vagas
[2026-06-12 19:59:50] [Tentativa 1] Inscrevendo em: Enfermaria
[2026-06-12 19:59:52] ✓ Inscrição realizada na vaga XYZ123
```

## 🆘 Troubleshooting

| Problema | Solução |
|----------|---------|
| Falha no login | Verifique SISVEP_MATRICULA e SISVEP_SENHA |
| Nenhuma vaga encontrada | Confirme vagas abertas no portal |
| Workflow não roda no horário | GitHub pode ter atraso de até 5 min |

---

**Criado com ❤️ para automação de voluntários SEAPE**
