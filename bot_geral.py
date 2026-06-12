#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT-GERAL - Automacao SIMPLES de Pesquisa e Inscricao de Voluntarios SEAPE
==========================================================================
Plano B do sisvep-bot: sem perguntas no Telegram. Pega TODAS as vagas
disponiveis e tenta se inscrever em todas.

Modos (variavel de ambiente MODO):
  pesquisa  -> loga, pesquisa todas as vagas e avisa no Telegram
  inscricao -> loga, pesquisa todas as vagas e tenta inscrever em todas

Baseado no formulario REAL do SISVEP (pesquisa.xhtml / inscricao.xhtml),
inspecionado em sessao autenticada em 12/06/2026. Os campos sao localizados
DINAMICAMENTE (pelos rotulos/opcoes), para nao quebrar quando o PrimeFaces
muda os IDs auto-gerados.

Secrets no GitHub:
  SISVEP_MATRICULA, SISVEP_SENHA  (obrigatorios)
  TG_TOKEN, TG_CHAT_ID            (opcionais - notificacoes)
  MODO                            (pesquisa | inscricao)

NOTA: a confirmacao da inscricao exige re-autenticacao (usuario+senha). O
passo de inscricao e best-effort e so reporta SUCESSO com confirmacao
explicita do site (nunca por simples HTTP 200).
"""

import os
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot-geral")

MATRICULA = os.environ.get("SISVEP_MATRICULA", "")
SENHA = os.environ.get("SISVEP_SENHA", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
MODO = os.environ.get("MODO", "pesquisa").strip().lower()

BASE_URL = "https://voluntario.seape.df.gov.br"
LOGIN_URL = f"{BASE_URL}/login.xhtml"                       # CORRIGIDO
PESQUISA_URL = f"{BASE_URL}/paginas/voluntario/pesquisa.xhtml"
INSCRICAO_URL = f"{BASE_URL}/paginas/voluntario/inscricao.xhtml"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def criar_sessao():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def enviar_telegram(mensagem):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT_ID, "text": mensagem}, timeout=10)
    except Exception as e:
        log.warning(f"Telegram falhou: {e}")


def _viewstate(soup):
    el = soup.find("input", {"name": "javax.faces.ViewState"})
    return el.get("value") if el else None


# ---------------------------------------------------------------------------
# Login (JSF: GET -> ViewState -> POST com campos reais)
# ---------------------------------------------------------------------------

def fazer_login(sessao):
    try:
        log.info("Acessando login...")
        r = sessao.get(LOGIN_URL, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        vs = _viewstate(soup)
        if not vs:
            log.error("ViewState nao encontrado")
            return False

        form = soup.find("form")
        if not form:
            log.error("Form de login nao encontrado")
            return False
        form_id = form.get("id", "frm")
        action = form.get("action", LOGIN_URL)
        if not action.startswith("http"):
            action = BASE_URL + action

        # base com todos os hidden
        payload = {}
        for inp in form.find_all("input"):
            nome = inp.get("name")
            if nome and inp.get("type", "text").lower() not in ("submit", "button", "image"):
                payload[nome] = inp.get("value", "")

        # detecta campos de texto (matricula) e senha dinamicamente
        textos = [i for i in form.find_all("input")
                  if i.get("type", "text").lower() in ("text", "email", "") and i.get("name")]
        senhas = [i for i in form.find_all("input")
                  if i.get("type", "").lower() == "password" and i.get("name")]
        if textos:
            payload[textos[0]["name"]] = MATRICULA
        if senhas:
            payload[senhas[0]["name"]] = SENHA

        # botao de submit
        btn = form.find("button", {"type": "submit"}) or form.find("input", {"type": "submit"})
        if btn and btn.get("name"):
            payload[btn["name"]] = btn.get("value", "")
        if form_id:
            payload[form_id] = form_id
        payload["javax.faces.ViewState"] = vs

        r2 = sessao.post(action, data=payload, timeout=20, allow_redirects=True)
        txt = r2.text.lower()
        ok = ("login.xhtml" not in r2.url.lower()) or ("sair" in txt) or ("logout" in txt)
        if ok:
            log.info("Login OK")
        else:
            log.error("Login falhou (continua na pagina de login)")
        return ok
    except Exception as e:
        log.error(f"Erro no login: {e}")
        return False


# ---------------------------------------------------------------------------
# Pesquisa (form real frmPrincipal, campos localizados dinamicamente)
# ---------------------------------------------------------------------------

def _form_pesquisa(soup):
    for b in soup.find_all(["button", "input"]):
        if "pesquisar vagas" in (b.get_text() or b.get("value") or "").lower():
            return b.find_parent("form")
    return soup.find("form", {"id": "frmPrincipal"}) or soup.find("form")


def _select_por_opcao(form, texto):
    for sel in form.find_all("select"):
        for opt in sel.find_all("option"):
            if texto.lower() in opt.get_text().strip().lower():
                return sel.get("name")
    return None


def _campo_data(form):
    for inp in form.find_all("input"):
        if (inp.get("id", "") or "").endswith("_input"):
            return inp.get("name")
    return None


def _nome_botao(form):
    for b in form.find_all(["button", "input"]):
        if "pesquisar vagas" in (b.get_text() or b.get("value") or "").lower():
            return b.get("name")
    return None


def _serializar_form(form):
    dados = {}
    for inp in form.find_all("input"):
        nome = inp.get("name")
        if not nome:
            continue
        tipo = (inp.get("type") or "text").lower()
        if tipo in ("checkbox", "radio") and not inp.has_attr("checked"):
            continue
        dados[nome] = inp.get("value", "")
    for sel in form.find_all("select"):
        nome = sel.get("name")
        if not nome:
            continue
        op = sel.find("option", selected=True) or sel.find("option")
        dados[nome] = op.get("value", "") if op else ""
    for ta in form.find_all("textarea"):
        if ta.get("name"):
            dados[ta.get("name")] = ta.get_text()
    return dados


def parse_vagas(html):
    """Extrai vagas de tabelaVagasDisponiveis.
    Colunas: Cod.Vaga | Qtd | Qtd Disponivel | Data/Hora | Jornada | Unidade | Selecionar
    """
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.find(id=lambda x: x and "tabelaVagasDisponiveis" in x)
    if not tabela:
        return []
    vagas = []
    corpo = tabela.find("tbody") or tabela
    for tr in corpo.find_all("tr"):
        cels = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cels) < 6:
            continue
        vagas.append({
            "codigo": cels[0], "qtd": cels[1], "qtd_disponivel": cels[2],
            "data_hora": cels[3], "jornada": cels[4], "unidade": cels[5],
        })
    return vagas


def pesquisar_vagas(sessao):
    """Pesquisa TODAS as vagas disponiveis (sem filtro)."""
    try:
        log.info("Acessando pesquisa...")
        r = sessao.get(PESQUISA_URL, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        form = _form_pesquisa(soup)
        if form is None:
            log.warning("Form de pesquisa nao encontrado")
            return []
        dados = _serializar_form(form)
        # sem filtro: unidade/jornada = "" (Todas)
        for nome in (_select_por_opcao(form, "Todas as Unidades"),
                     _select_por_opcao(form, "Todas as Jornadas")):
            if nome:
                dados[nome] = ""
        botao = _nome_botao(form)
        if botao:
            dados[botao] = dados.get(botao, "")
        r2 = sessao.post(PESQUISA_URL, data=dados, timeout=20)
        vagas = parse_vagas(r2.text)
        log.info(f"Encontradas {len(vagas)} vaga(s)")
        return vagas
    except Exception as e:
        log.error(f"Erro na pesquisa: {e}")
        return []


# ---------------------------------------------------------------------------
# Inscricao (best-effort; exige re-autenticacao usuario+senha)
# ---------------------------------------------------------------------------

def inscrever_vaga(sessao, codigo):
    """
    Tenta inscrever na vaga pelo codigo, na pagina inscricao.xhtml.
    OBS: o fluxo real e selecionar a linha + re-autenticar. Como o diálogo de
    re-auth so existe quando ha vaga, este passo nao foi validado ao vivo.
    So reporta SUCESSO com marcador explicito.
    """
    try:
        r = sessao.get(INSCRICAO_URL, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        form = _form_pesquisa(soup) or soup.find("form")
        if not form:
            return False
        dados = _serializar_form(form)
        # informa o codigo da vaga no campo de codigo, se existir
        for inp in form.find_all("input"):
            _id = (inp.get("id") or "").lower()
            if "codigo" in _id or "j_idt49" in _id:
                dados[inp.get("name")] = codigo
        # re-autenticacao: preenche eventuais campos usuario/senha presentes
        for inp in form.find_all("input"):
            tipo = (inp.get("type") or "").lower()
            if tipo == "password" and inp.get("name"):
                dados[inp.get("name")] = SENHA
        vs = _viewstate(soup)
        if vs:
            dados["javax.faces.ViewState"] = vs
        r2 = sessao.post(INSCRICAO_URL, data=dados, timeout=20)
        t = r2.text.lower()
        if any(m in t for m in ("inscricao realizada", "inscrito com sucesso", "sucesso")):
            return True
        return False
    except Exception as e:
        log.error(f"Erro ao inscrever {codigo}: {e}")
        return False


def inscrever_em_todas(sessao, vagas, duracao_segundos=50):
    if not vagas:
        log.warning("Nenhuma vaga para inscrever")
        return
    log.info(f"Inscricao continua em {len(vagas)} vaga(s) por {duracao_segundos}s")
    inicio = time.time()
    inscritas = set()
    tentativa = 0
    while (time.time() - inicio) < duracao_segundos:
        tentativa += 1
        for v in vagas:
            cod = v.get("codigo")
            if not cod or cod in inscritas:
                continue
            if inscrever_vaga(sessao, cod):
                inscritas.add(cod)
                log.info(f"Inscrito: vaga {cod}")
                enviar_telegram(f"Inscrito: vaga {cod} - {v.get('data_hora','')} "
                                f"{v.get('unidade','')}")
            time.sleep(0.3)
        time.sleep(0.5)
    log.info(f"Fim. Total inscrito: {len(inscritas)}/{len(vagas)}")
    if inscritas:
        enviar_telegram(f"Inscricao finalizada: {len(inscritas)} vaga(s).")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    log.info(f"BOT-GERAL iniciando | MODO={MODO}")
    if not MATRICULA or not SENHA:
        log.error("SISVEP_MATRICULA/SISVEP_SENHA nao configurados")
        sys.exit(1)

    sessao = criar_sessao()
    if not fazer_login(sessao):
        enviar_telegram("BOT-GERAL: falha no login.")
        sys.exit(1)

    vagas = pesquisar_vagas(sessao)

    if not vagas:
        enviar_telegram("BOT-GERAL: nenhuma vaga disponivel no momento.")
        log.info("Sem vagas.")
        return

    resumo = "\n".join(f"- {v['codigo']} | {v['data_hora']} | {v['unidade']} | "
                       f"{v['jornada']} | {v['qtd_disponivel']} disp."
                       for v in vagas)
    enviar_telegram(f"BOT-GERAL: {len(vagas)} vaga(s) encontrada(s):\n{resumo}")

    if MODO == "inscricao":
        inscrever_em_todas(sessao, vagas)
    else:
        log.info("Modo pesquisa - apenas listagem (sem inscrever)")


# ---------------------------------------------------------------------------
# Autoteste do parser (SELFTEST=1, sem rede)
# ---------------------------------------------------------------------------

if __name__ == "__main__" and os.environ.get("SELFTEST"):
    vazio = '<table id="frmPrincipal:tabelaVagasDisponiveis"><tbody>' \
            '<tr><td colspan="7">Nao ha Vagas Disponiveis.</td></tr></tbody></table>'
    com = '<table id="frmPrincipal:tabelaVagasDisponiveis"><tbody>' \
          '<tr><td>1024</td><td>3</td><td>2</td><td>15/06/2026 08:00</td>' \
          '<td>8 h</td><td>CDP</td><td><button>Selecionar</button></td></tr></tbody></table>'
    assert parse_vagas(vazio) == []
    vs = parse_vagas(com)
    assert len(vs) == 1 and vs[0]["codigo"] == "1024" and vs[0]["unidade"] == "CDP", vs
    print("OK - parser bot-geral funcionando:", vs[0])
elif __name__ == "__main__":
    main()
