#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT-GERAL — Automação de Pesquisa e Inscrição de Voluntários
================================================================
Executa em dois momentos:

1. 19:58 BRT → Pesquisa todos os voluntários vagos disponíveis
2. 19:59:50-20:00:40 BRT → Inscreve automaticamente em TODAS as vagas encontradas

Secrets necessários no GitHub:
  SISVEP_MATRICULA  — sua matrícula
  SISVEP_SENHA      — sua senha
  TG_TOKEN          — token do bot Telegram (opcional, para notificações)
  TG_CHAT_ID        — seu chat ID no Telegram (opcional)
"""

import os
import re
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("bot-geral")

MATRICULA = os.environ.get("SISVEP_MATRICULA", "")
SENHA = os.environ.get("SISVEP_SENHA", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
MODO = os.environ.get("MODO", "pesquisa")  # "pesquisa" ou "inscricao"

BASE_URL = "https://voluntario.seape.df.gov.br"
LOGIN_URL = f"{BASE_URL}/paginas/voluntario/login.xhtml"
PESQUISA_URL = f"{BASE_URL}/paginas/voluntario/pesquisa.xhtml"
INSCRICAO_URL = f"{BASE_URL}/paginas/voluntario/inscricao.xhtml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

AJAX_HEADERS = {
    **HEADERS,
    "Faces-Request": "partial/ajax",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def hora():
    return datetime.now().strftime("%H:%M:%S")

def criar_sessao() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def get_viewstate(soup: BeautifulSoup) -> str:
    el = soup.find("input", {"name": "javax.faces.ViewState"})
    if not el:
        raise RuntimeError("ViewState não encontrado")
    return el["value"]

def enviar_telegram(mensagem: str):
    """Envia mensagem ao Telegram (opcional)"""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": mensagem})
    except Exception as e:
        log.warning(f"Não foi possível enviar ao Telegram: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def fazer_login(sessao: requests.Session) -> bool:
    """Faz login no sistema"""
    try:
        log.info("Acessando página de login...")
        resp = sessao.get(LOGIN_URL)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        viewstate = get_viewstate(soup)

        # Descobrir nomes dos campos dinamicamente
        form = soup.find("form")
        inputs = form.find_all("input", {"type": "text"})
        password_input = form.find("input", {"type": "password"})
        button = form.find("button") or form.find("input", {"type": "submit"})

        if not inputs or not password_input or not button:
            raise RuntimeError("Não foi possível encontrar campos do formulário")

        username_name = inputs[0]["name"]
        password_name = password_input["name"]
        button_name = button.get("name", "")

        log.info(f"Fazendo login com matrícula: {MATRICULA}")

        data = {
            username_name: MATRICULA,
            password_name: SENHA,
            "javax.faces.ViewState": viewstate,
        }

        if button_name:
            data[button_name] = button.get("value", "")

        resp = sessao.post(LOGIN_URL, data=data)
        resp.raise_for_status()

        if "login" in resp.url.lower() or "erro" in resp.text.lower():
            log.error("Falha no login")
            return False

        log.info("✓ Login realizado com sucesso")
        return True

    except Exception as e:
        log.error(f"Erro no login: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# PESQUISA DE VAGAS
# ─────────────────────────────────────────────────────────────────────────────

def pesquisar_vagas(sessao: requests.Session) -> list:
    """
    Pesquisa todas as vagas disponíveis.
    Retorna lista de dicionários com dados das vagas.
    """
    try:
        log.info("Acessando página de pesquisa...")
        resp = sessao.get(PESQUISA_URL)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Procura por tabela de vagas
        tabela = soup.find("table")
        if not tabela:
            log.warning("Nenhuma tabela de vagas encontrada")
            return []

        vagas = []
        linhas = tabela.find_all("tr")[1:]  # Pula cabeçalho

        for linha in linhas:
            cels = linha.find_all("td")
            if len(cels) < 3:
                continue

            # Extrair dados da vaga
            data = cels[0].get_text(strip=True)
            horario = cels[1].get_text(strip=True)
            atividade = cels[2].get_text(strip=True)
            status = cels[3].get_text(strip=True) if len(cels) > 3 else "Disponível"

            # Procura por botão de ação
            link = linha.find("a")
            botao = linha.find("button")

            vaga = {
                "data": data,
                "horario": horario,
                "atividade": atividade,
                "status": status,
                "disponivel": "vago" in status.lower() or "disponível" in status.lower()
            }

            if link:
                vaga["link"] = link.get("href", "")
                vaga["id"] = re.search(r"id=(\w+)", vaga["link"]).group(1) if re.search(r"id=(\w+)", vaga["link"]) else ""

            vagas.append(vaga)

        log.info(f"✓ Encontradas {len(vagas)} vagas")
        return vagas

    except Exception as e:
        log.error(f"Erro na pesquisa: {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# INSCRIÇÃO EM VAGAS
# ─────────────────────────────────────────────────────────────────────────────

def inscrever_vaga(sessao: requests.Session, vaga_id: str) -> bool:
    """Tenta inscrever em uma vaga específica"""
    try:
        resp = sessao.get(f"{INSCRICAO_URL}?id={vaga_id}")
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        viewstate = get_viewstate(soup)

        # Procura por campos do formulário
        form = soup.find("form")
        if not form:
            log.warning(f"Formulário não encontrado para vaga {vaga_id}")
            return False

        # Encontra botão de confirmação
        button = form.find("button") or form.find("input", {"type": "submit"})
        if not button:
            log.warning(f"Botão de confirmação não encontrado para vaga {vaga_id}")
            return False

        button_name = button.get("name", "")

        # Monta dados da requisição
        data = {
            "javax.faces.ViewState": viewstate,
        }

        if button_name:
            data[button_name] = button.get("value", "")

        # Faz requisição AJAX
        resp = sessao.post(INSCRICAO_URL, data=data, headers=AJAX_HEADERS)
        resp.raise_for_status()

        if "sucesso" in resp.text.lower() or "inscrit" in resp.text.lower():
            log.info(f"✓ Inscrição realizada na vaga {vaga_id}")
            return True
        else:
            log.warning(f"Resposta ambígua na inscrição da vaga {vaga_id}")
            return False

    except Exception as e:
        log.error(f"Erro ao inscrever em vaga {vaga_id}: {e}")
        return False

def inscrever_continuo(sessao: requests.Session, vagas: list, duracao_segundos: int = 50):
    """
    Tenta inscrever em todas as vagas repetidamente por N segundos.
    Inicia 10 segundos antes das 20:00 (19:59:50).
    """
    if not vagas:
        log.warning("Nenhuma vaga disponível para inscrição")
        return

    log.info(f"Iniciando inscrição contínua em {len(vagas)} vaga(s) por {duracao_segundos} segundos")

    tempo_inicio = time.time()
    tentativa = 1
    inscritas = set()

    while (time.time() - tempo_inicio) < duracao_segundos:
        for vaga in vagas:
            vaga_id = vaga.get("id", "")
            if not vaga_id or vaga_id in inscritas:
                continue

            log.info(f"[Tentativa {tentativa}] Inscrevendo em: {vaga['atividade']} ({vaga['data']} {vaga['horario']})")

            if inscrever_vaga(sessao, vaga_id):
                inscritas.add(vaga_id)
                enviar_telegram(f"✓ Inscrito com sucesso em:\n{vaga['atividade']}\n{vaga['data']} {vaga['horario']}")

            time.sleep(0.5)  # Pequeno delay entre vagas

        tentativa += 1
        tempo_decorrido = int(time.time() - tempo_inicio)
        tempo_restante = duracao_segundos - tempo_decorrido

        if tempo_restante > 0:
            log.info(f"Aguardando {tempo_restante}s antes da próxima rodada...")
            time.sleep(min(5, tempo_restante))

    log.info(f"Inscrição contínua finalizada. Total inscrito: {len(inscritas)}")
    return len(inscritas)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log.info(f"BOT-GERAL iniciado às {hora()} - Modo: {MODO}")

    if not MATRICULA or not SENHA:
        log.error("SISVEP_MATRICULA e SISVEP_SENHA não configurados")
        sys.exit(1)

    sessao = criar_sessao()

    if not fazer_login(sessao):
        log.error("Não foi possível fazer login")
        enviar_telegram("❌ BOT-GERAL: Falha no login")
        sys.exit(1)

    if MODO == "pesquisa":
        log.info("=== MODO PESQUISA ===")
        vagas = pesquisar_vagas(sessao)

        if vagas:
            mensagem = f"🔍 BOT-GERAL - {len(vagas)} vaga(s) encontrada(s):\n\n"
            for v in vagas[:5]:  # Primeiras 5
                mensagem += f"• {v['atividade']}\n  {v['data']} {v['horario']}\n"
            if len(vagas) > 5:
                mensagem += f"\n... e mais {len(vagas) - 5}"
            enviar_telegram(mensagem)
        else:
            enviar_telegram("⚠️ BOT-GERAL: Nenhuma vaga encontrada")

    elif MODO == "inscricao":
        log.info("=== MODO INSCRIÇÃO ===")
        vagas = pesquisar_vagas(sessao)

        if vagas:
            total_inscrito = inscrever_continuo(sessao, vagas, duracao_segundos=50)
            enviar_telegram(f"📝 BOT-GERAL: Inscrição contínua finalizada. Total: {total_inscrito}")
        else:
            log.warning("Nenhuma vaga encontrada para inscrição")
            enviar_telegram("⚠️ BOT-GERAL: Nenhuma vaga para inscrição")

    log.info("BOT-GERAL finalizado")

if __name__ == "__main__":
    main()
