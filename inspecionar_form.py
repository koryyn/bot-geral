#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspeciona o formulário de login e lista TODOS os campos
"""

import requests
from bs4 import BeautifulSoup
import re

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

print("=" * 80)
print("INSPECIONANDO FORMULÁRIO DE LOGIN DO SEAPE")
print("=" * 80)
print()

try:
    resp = requests.get(LOGIN_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form")

    if not form:
        print("❌ Formulário não encontrado!")
        exit(1)

    print("TODOS OS INPUTS DO FORMULÁRIO:")
    print("-" * 80)
    print()

    inputs = form.find_all("input")

    for i, inp in enumerate(inputs):
        name = inp.get("name", "SEM NAME")
        input_type = inp.get("type", "text")
        input_id = inp.get("id", "")
        value = inp.get("value", "")

        # Truncar valor se for muito grande
        if len(str(value)) > 100:
            value_display = str(value)[:100] + "... [truncado]"
        else:
            value_display = value

        print(f"[{i}] NAME: {name}")
        print(f"    TYPE: {input_type}")
        print(f"    ID: {input_id}")
        print(f"    VALUE: {value_display}")
        print()

    print("=" * 80)
    print("BOTÕES DO FORMULÁRIO:")
    print("-" * 80)
    print()

    buttons = form.find_all("button")

    for i, btn in enumerate(buttons):
        name = btn.get("name", "SEM NAME")
        btn_type = btn.get("type", "submit")
        value = btn.get("value", "")
        text = btn.get_text(strip=True)

        print(f"[{i}] NAME: {name}")
        print(f"    TYPE: {btn_type}")
        print(f"    VALUE: {value}")
        print(f"    TEXT: {text}")
        print()

    print("=" * 80)
    print("RESUMO:")
    print("-" * 80)
    print()
    print(f"Total de inputs: {len(inputs)}")
    print(f"Total de botões: {len(buttons)}")
    print()

    # Listar todos os nomes de campos que o bot precisa enviar
    print("CAMPOS QUE O BOT PRECISA ENVIAR NO POST:")
    print("-" * 80)
    for inp in inputs:
        name = inp.get("name")
        if name:
            print(f"   - {name}")

    for btn in buttons:
        name = btn.get("name")
        if name:
            print(f"   - {name} (botão)")

except Exception as e:
    print(f"❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
