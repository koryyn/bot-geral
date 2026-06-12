#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug do login - procura por mensagens de erro
"""

import requests
from bs4 import BeautifulSoup
import re
import os

LOGIN_URL = 'https://voluntario.seape.df.gov.br/paginas/voluntario/login.xhtml'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

MATRICULA = os.environ.get("SISVEP_MATRICULA", "").strip()
SENHA = os.environ.get("SISVEP_SENHA", "").strip()

print("=" * 70)
print("DEBUG - PROCURANDO MENSAGENS DE ERRO")
print("=" * 70)
print()

sessao = requests.Session()
sessao.headers.update(HEADERS)
resp = sessao.get(LOGIN_URL)
soup = BeautifulSoup(resp.text, 'html.parser')

viewstate = soup.find('input', {'id': re.compile(r'ViewState')})['value']
viewstate_name = soup.find('input', {'id': re.compile(r'ViewState')}).get('id', 'javax.faces.ViewState')

data = {
    'username': MATRICULA,
    'password': SENHA,
    viewstate_name: viewstate,
    'btnEmitir': 'Entrar'
}

resp = sessao.post(LOGIN_URL, data=data)
soup_resp = BeautifulSoup(resp.text, 'html.parser')

print('PROCURANDO POR MENSAGENS DE ERRO')
print("=" * 70)

# Procurar spans/divs com mensagens
spans = soup_resp.find_all(['span', 'div', 'p'])
encontrou_erro = False

for span in spans:
    text = span.get_text(strip=True)
    if text and any(palavra in text.lower() for palavra in ['erro', 'invalido', 'falha', 'incorreto', 'senha', 'usuario', 'blocked', 'bloqueado']):
        if len(text) < 300:
            print(f'   {text}')
            encontrou_erro = True

if not encontrou_erro:
    print("   (Nenhuma mensagem de erro encontrada)")

print()
print("=" * 70)
print("TODOS OS INPUTS NO FORMULARIO")
print("=" * 70)

form = soup_resp.find('form')
if form:
    inputs = form.find_all('input')
    for inp in inputs:
        name = inp.get('name', 'SEM NAME')
        input_type = inp.get('type', 'text')
        input_id = inp.get('id', '')
        print(f'   Name: {name:30} | Type: {input_type:10} | ID: {input_id}')

print()
print("=" * 70)
print("ANALISANDO RESULTADO")
print("=" * 70)
print()

if "login" in resp.url.lower():
    print("❌ LOGIN FALHOU")
    print()
    print("Possíveis causas:")
    print("   1. Matrícula ou senha INCORRETA")
    print("   2. Conta BLOQUEADA")
    print("   3. Portal exigindo campos adicionais (CAPTCHA, etc)")
    print()
    print("Próximo passo:")
    print("   ✅ Verifique se consegue fazer login MANUALMENTE no site")
    print("      https://voluntario.seape.df.gov.br/paginas/voluntario/login.xhtml")
    print()
    print("   Se conseguir login manual com essas credenciais, o problema é:")
    print("   - Headers faltando")
    print("   - Validações extras que o portal exige")
else:
    print("✅ LOGIN APARENTEMENTE OK!")
    print(f"   URL: {resp.url}")

print()
