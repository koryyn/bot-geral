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

def get_viewstate(soup: BeautifulSoup) -> str:
    """Extrai o ViewState da página"""
    el = soup.find("input", {"name": "javax.faces.ViewState"})
    if not el:
        raise RuntimeError("ViewState não encontrado na página")
    return el["value"]


def fazer_login(sessao: requests.Session) -> bool:
    """
    Faz login descobrindo os campos do formulário dinamicamente,
    sem depender de IDs que podem mudar entre versões do JSF.
    """
    try:
        log.info("Acessando página de login...")
        r = sessao.get(LOGIN_URL, timeout=20)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        vs = get_viewstate(soup)

        # Descobre o formulário de login
        form = soup.find("form")
        if not form:
            log.error("Formulário de login não encontrado")
            return False

        form_id = form.get("id", "")
        action = form.get("action", LOGIN_URL)
        if not action.startswith("http"):
            action = BASE_URL + action

        # Monta o payload base com todos os campos hidden
        payload = {}
        for inp in form.find_all("input"):
            name = inp.get("name", "")
            value = inp.get("value", "")
            tipo = inp.get("type", "text").lower()
            if name and tipo not in ("submit", "button", "image"):
                payload[name] = value

        # Sobrescreve ViewState
        payload["javax.faces.ViewState"] = vs

        # Preenche matrícula e senha detectando os campos pelo tipo e nome
        campos_texto = [
            i for i in form.find_all("input")
            if i.get("type", "text").lower() in ("text", "email", "") and i.get("name")
        ]
        campos_senha = [
            i for i in form.find_all("input")
            if i.get("type", "").lower() == "password" and i.get("name")
        ]

        if campos_texto:
            payload[campos_texto[0]["name"]] = MATRICULA
            log.info(f"Campo matrícula: {campos_texto[0]['name']}")
        else:
            # Fallback para nomes comuns
            for nome in ("username", "j_username", "cpf", "matricula"):
                if nome in payload:
                    payload[nome] = MATRICULA
                    break

        if campos_senha:
            payload[campos_senha[0]["name"]] = SENHA
            log.info(f"Campo senha: {campos_senha[0]['name']}")
        else:
            for nome in ("password", "j_password", "senha"):
                if nome in payload:
                    payload[nome] = SENHA
                    break

        # Adiciona o botão de submit se encontrado
        btn = form.find("button", {"type": "submit"}) or form.find("input", {"type": "submit"})
        if btn and btn.get("name"):
            payload[btn["name"]] = btn.get("value", "Entrar")

        # Se formulário tem id, inclui no payload (padrão JSF)
        if form_id:
            payload[form_id] = form_id

        log.info(f"Fazendo login com matrícula: {MATRICULA}")
        r2 = sessao.post(action, data=payload, timeout=20, allow_redirects=True)

        # Verifica falha de login
        if "login" in r2.url.lower():
            soup2 = BeautifulSoup(r2.text, "html.parser")
            erro = soup2.find(string=re.compile(r"inválid|incorret|erro|invalid", re.I))
            if erro:
                log.error(f"Falha no login: {erro.strip()}")
                return False
            if "login" in r2.url.lower() and "paginas" not in r2.url.lower():
                log.warning("Redirecionou para login — credenciais podem estar erradas")
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

        # Procura pelo ViewState
        viewstate_input = soup.find("input", {"id": re.compile(r"ViewState")})
        if not viewstate_input:
            viewstate_input = soup.find("input", {"name": "javax.faces.ViewState"})

        if not viewstate_input:
            log.warning(f"ViewState não encontrado para vaga {vaga_id}")
            return False

        viewstate = viewstate_input["value"]
        viewstate_name = viewstate_input.get("id", "javax.faces.ViewState")

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
            viewstate_name: viewstate,
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