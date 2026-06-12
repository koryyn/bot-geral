#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisa a página de login do SEAPE para descobrir a estrutura do formulário
"""

import requests
from bs4 import BeautifulSoup
import re

print("=" * 70)
print("ANALISANDO PÁGINA DE LOGIN DO SEAPE")
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

try:
    print("Acessando página de login...")
    resp = requests.get(LOGIN_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    print("✅ Página acessada com sucesso!")
    print()

    # 1. Procurar ViewState
    print("=" * 70)
    print("1. PROCURANDO VIEWSTATE")
    print("=" * 70)

    # Por ID
    viewstate_input = soup.find("input", {"id": re.compile(r"ViewState")})
    if viewstate_input:
        print(f"✅ Encontrado por ID:")
        print(f"   ID: {viewstate_input.get('id')}")
        print(f"   Name: {viewstate_input.get('name')}")
        print(f"   Value length: {len(viewstate_input.get('value', ''))}")
    else:
        print("❌ Não encontrado por ID")

    # Por name
    viewstate_input_name = soup.find("input", {"name": "javax.faces.ViewState"})
    if viewstate_input_name:
        print(f"✅ Encontrado por name 'javax.faces.ViewState':")
        print(f"   ID: {viewstate_input_name.get('id')}")
        print(f"   Name: {viewstate_input_name.get('name')}")
    else:
        print("❌ Não encontrado por name 'javax.faces.ViewState'")

    # Todos os inputs
    print()
    print("Todos os inputs da página:")
    form = soup.find("form")
    if form:
        inputs = form.find_all("input")
        for inp in inputs:
            input_type = inp.get("type", "text")
            input_name = inp.get("name", "SEM NAME")
            input_id = inp.get("id", "SEM ID")
            print(f"   Type: {input_type:10} | Name: {input_name:40} | ID: {input_id}")

    print()

    # 2. Procurar campos username/password
    print("=" * 70)
    print("2. PROCURANDO CAMPOS USERNAME/PASSWORD")
    print("=" * 70)

    username_input = form.find("input", {"name": "username"})
    if username_input:
        print(f"✅ Campo 'username' encontrado: {username_input.get('id')}")
    else:
        print("❌ Campo 'username' NÃO encontrado")

    password_input = form.find("input", {"name": "password"})
    if password_input:
        print(f"✅ Campo 'password' encontrado: {password_input.get('id')}")
    else:
        print("❌ Campo 'password' NÃO encontrado")

    print()

    # 3. Procurar botões
    print("=" * 70)
    print("3. PROCURANDO BOTÕES")
    print("=" * 70)

    buttons = form.find_all("button")
    print(f"Total de botões: {len(buttons)}")
    for i, btn in enumerate(buttons):
        btn_name = btn.get("name", "SEM NAME")
        btn_type = btn.get("type", "submit")
        btn_value = btn.get("value", "")
        btn_text = btn.get_text(strip=True)
        print(f"   [{i}] Type: {btn_type:10} | Name: {btn_name:20} | Text: '{btn_text}' | Value: {btn_value}")

    # Procurar por btnEmitir
    btn_emitir = form.find("button", {"name": "btnEmitir"})
    if btn_emitir:
        print(f"✅ Botão 'btnEmitir' encontrado")
    else:
        print(f"❌ Botão 'btnEmitir' NÃO encontrado")

    print()

    # 4. Resumo
    print("=" * 70)
    print("RESUMO PARA CORREÇÃO")
    print("=" * 70)
    print()

    all_good = all([
        viewstate_input or viewstate_input_name,
        username_input,
        password_input,
        btn_emitir or len(buttons) > 0
    ])

    if all_good:
        print("✅ TODOS OS CAMPOS ENCONTRADOS!")
        print("O código atual DEVERIA funcionar...")
        print()
        print("Se ainda está falhando, o problema pode ser:")
        print("  1. Dados de login inválidos (matricula/senha errados)")
        print("  2. Resposta do servidor não indica sucesso corretamente")
        print("  3. Portal usa CAPTCHA ou autenticação extra")
    else:
        print("❌ CAMPOS FALTANDO!")
        print("Valores encontrados:")
        print(f"   ViewState: {bool(viewstate_input or viewstate_input_name)}")
        print(f"   Username: {bool(username_input)}")
        print(f"   Password: {bool(password_input)}")
        print(f"   Botão: {bool(btn_emitir or buttons)}")

except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
