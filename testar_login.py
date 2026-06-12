#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa o login de verdade para ver qual é a resposta
"""

import requests
from bs4 import BeautifulSoup
import re
import os

print("=" * 70)
print("TESTANDO LOGIN NO SEAPE")
print("=" * 70)
print()

LOGIN_URL = "https://voluntario.seape.df.gov.br/paginas/voluntario/login.xhtml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Obter credenciais
MATRICULA = os.environ.get("SISVEP_MATRICULA", "").strip()
SENHA = os.environ.get("SISVEP_SENHA", "").strip()

print(f"Matrícula configurada: {'SIM' if MATRICULA else 'NÃO'}")
print(f"Senha configurada: {'SIM' if SENHA else 'NÃO'}")
print()

if not MATRICULA or not SENHA:
    print("❌ ERRO: Configure as variáveis de ambiente:")
    print('   $env:SISVEP_MATRICULA = "sua_matricula"')
    print('   $env:SISVEP_SENHA = "sua_senha"')
    print()
    print("Exemplo:")
    print('   $env:SISVEP_MATRICULA = "123456"')
    print('   $env:SISVEP_SENHA = "abc123"')
    exit(1)

try:
    print("Step 1: Acessando página de login...")
    sessao = requests.Session()
    sessao.headers.update(HEADERS)

    resp = sessao.get(LOGIN_URL)
    resp.raise_for_status()
    print(f"✅ Status: {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")
    viewstate_input = soup.find("input", {"id": re.compile(r"ViewState")})

    if not viewstate_input:
        viewstate_input = soup.find("input", {"name": "javax.faces.ViewState"})

    viewstate = viewstate_input["value"]
    viewstate_name = viewstate_input.get("id", "javax.faces.ViewState")

    print(f"✅ ViewState obtido (length: {len(viewstate)})")
    print()

    print("Step 2: Montando dados de login...")
    form = soup.find("form")
    username_input = form.find("input", {"name": "username"})
    password_input = form.find("input", {"name": "password"})
    button = form.find("button", {"name": "btnEmitir"})

    data = {
        "username": MATRICULA,
        "password": SENHA,
        viewstate_name: viewstate,
        "btnEmitir": "Entrar"
    }

    print(f"   Username: {MATRICULA}")
    print(f"   Password: {'*' * len(SENHA)}")
    print(f"   ViewState name: {viewstate_name}")
    print(f"   Button: btnEmitir")
    print()

    print("Step 3: Enviando login...")
    resp = sessao.post(LOGIN_URL, data=data)
    resp.raise_for_status()

    print(f"✅ Status: {resp.status_code}")
    print(f"   URL final: {resp.url}")
    print()

    print("Step 4: Verificando resposta...")
    print(f"   'login' em URL: {'SIM' if 'login' in resp.url.lower() else 'NÃO'}")
    print(f"   'erro' em texto: {'SIM' if 'erro' in resp.text.lower() else 'NÃO'}")
    print(f"   'sucesso' em texto: {'SIM' if 'sucesso' in resp.text.lower() else 'NÃO'}")
    print(f"   'inscrit' em texto: {'SIM' if 'inscrit' in resp.text.lower() else 'NÃO'}")
    print()

    print("Step 5: Analisando resultado...")

    # Verificação original
    if "login" in resp.url.lower() or ("erro" in resp.text.lower() and "login" in resp.text.lower()):
        print("❌ FALHA NO LOGIN (segundo o código original)")
    else:
        print("✅ LOGIN APARENTEMENTE OK (segundo o código original)")

    print()

    print("Step 6: Procurando mensagens de erro/sucesso...")
    soup_resp = BeautifulSoup(resp.text, "html.parser")

    # Procurar por divs com classe de erro/sucesso
    error_divs = soup_resp.find_all("div", {"class": re.compile(r"erro|error|fail", re.I)})
    success_divs = soup_resp.find_all("div", {"class": re.compile(r"sucesso|success", re.I)})

    if error_divs:
        print("Mensagens de erro encontradas:")
        for div in error_divs:
            text = div.get_text(strip=True)
            if text:
                print(f"   - {text}")

    if success_divs:
        print("Mensagens de sucesso encontradas:")
        for div in success_divs:
            text = div.get_text(strip=True)
            if text:
                print(f"   - {text}")

    # Procurar por spans/p com erro
    spans = soup_resp.find_all(["span", "p"], string=re.compile(r"erro|não|inválid", re.I))
    if spans and not error_divs:
        print("Possíveis mensagens de erro:")
        for span in spans[:3]:
            text = span.get_text(strip=True)
            if text and len(text) < 200:
                print(f"   - {text}")

    print()
    print("=" * 70)
    print("DIAGNÓSTICO")
    print("=" * 70)

    if "login" in resp.url.lower():
        print("🔴 PROBLEMA: URL ainda contém 'login'")
        print("   Provável causa: Credenciais inválidas ou sessão expirada")
        print()
        print("Dica: Verifique se:")
        print("   1. A matrícula está CORRETA")
        print("   2. A senha está CORRETA")
        print("   3. Sua conta não está bloqueada")
        print("   4. Você consegue fazer login manualmente no site")
    else:
        print("🟢 URL mudou (saiu de login)")
        print("   Provável: Login foi bem-sucedido!")
        print(f"   Nova URL: {resp.url}")

except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
