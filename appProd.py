# --- IMPORTS ---
import warnings
warnings.filterwarnings("ignore")

import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import time
import sys
import asyncio
import aiohttp
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------- PARTE 1: SGI (wilab) -------------------- #
LOGIN_URL = "https://sgi.claro.amx/auth/local"
GRAPHQL_URL = "https://sgi.claro.amx/api/graphql"

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Origin": "https://sgi.claro.amx",
    "Accept": "application/json"
}

LOGIN_CREDENCIALES = {
    "username": "EXA53410",
    "password": "Agosto.12"
}

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

QUERY = """
query EVENTS_AND_DEVICES($client_id: String!) {
  events: events_by_client_id(client_id: $client_id) {
    site {
      name
    }
    device {
      description {
        model
      }
    }
    name
    ts
    severity
    message
  }
}
"""

async def obtener_token():
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), headers=HEADERS_BASE) as session:
        try:
            async with session.post(LOGIN_URL, json=LOGIN_CREDENCIALES) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("token")
        except:
            return None

async def consultar_alarmas(token, cell_id):
    headers = {**HEADERS_BASE, "Authorization": f"Bearer {token}"}
    payload = {
        "operationName": "EVENTS_AND_DEVICES",
        "query": QUERY,
        "variables": {"client_id": cell_id}
    }

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), headers=headers) as session:
        try:
            async with session.post(GRAPHQL_URL, json=payload) as response:
                if response.status != 200:
                    return []
                data = await response.json()
                eventos = data.get("data", {}).get("events", [])
                resultados = []
                for e in eventos:
                    resultado = {
                        "site_name": e.get("site", {}).get("name"),
                        "device_model": e.get("device", {}).get("description", {}).get("model"),
                        "event_name": e.get("name"),
                        "alarma": e.get("message"),
                        "severity": e.get("severity"),
                        "fecha_creacion": e.get("ts")
                    }
                    if all(resultado.values()):
                        resultados.append(resultado)
                return resultados
        except:
            return []

# -------------------- PARTE 2: Giraweb -------------------- #
prefijos_por_gerencia = {
    "CFBA": ["CF"],
    "PACU": ["ME", "SJ", "SL", "COW", "SC", "CB", "TF", "RN", "NQ"],
    "MED": ["CO", "ST", "SE", "CT", "TU", "JU", "STR", "CTR", "RJ"],
    "LSUR": ["BA", "SF", "CH", "CR", "FO", "MI", "SJ", "ER"],
    "BLAP": ["BA", "PA", "PAR"]
}

urls_por_gerencia = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

def limpiar(texto):
    return texto.strip().replace('\n', ' ').replace('\r', '')

def formatear_cellid(cellid):
    letras = ''.join(filter(str.isalpha, cellid)).upper()
    numeros = ''.join(filter(str.isdigit, cellid)).zfill(5)
    return letras + numeros

def tiempo_en_dias(tiempo_texto):
    if not tiempo_texto:
        return 9999
    dias = horas = minutos = 0
    partes = tiempo_texto.split()
    for i, parte in enumerate(partes):
        if parte == 'd':
            dias = int(partes[i-1])
        elif parte == 'h':
            horas = int(partes[i-1])
        elif parte == 'm':
            minutos = int(partes[i-1])
    return dias + horas / 24 + minutos / 1440

def es_fila_alarma_valida(columnas):
    if len(columnas) != 6:
        return False
    site_id = limpiar(columnas[0].get_text(strip=True)).upper()
    ultima_columna = limpiar(columnas[-1].get_text(strip=True)).lower()
    if not (site_id.isalnum() and any(c.isalpha() for c in site_id) and any(c.isdigit() for c in site_id)):
        return False
    if ultima_columna.startswith(("+54", "sin salida", "sms", "whatsapp")):
        return False
    return True

def buscar_en_gerencia(nombre, url, session, cell_id_buscado):
    try:
        resp = session.get(url, timeout=8)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        filas = soup.find_all("tr")
        encontrados = []
        for fila in filas:
            columnas = fila.find_all("td")
            if columnas and es_fila_alarma_valida(columnas):
                try:
                    cell_id_actual = limpiar(columnas[0].get_text(strip=True)).upper()
                    if cell_id_actual == cell_id_buscado:
                        tiempo_texto = limpiar(columnas[-2].get_text(strip=True))
                        if tiempo_en_dias(tiempo_texto) < 3:
                            resultado = {
                                "site_id": cell_id_actual,
                                "fecha_creacion": limpiar(columnas[-3].get_text(strip=True)),
                                "alarma": limpiar(columnas[-1].get_text(strip=True))[:120] + "...",
                                "TIEMPO": tiempo_texto,
                                "cell_owner": limpiar(columnas[2].get_text(strip=True)),
                                "site_name": limpiar(columnas[1].get_text(strip=True))
                            }
                            if all(resultado.values()):
                                encontrados.append(resultado)
                except:
                    continue
        return encontrados
    except:
        return []


# -------------------- COORDINADOR -------------------- #

async def main():
    if len(sys.argv) < 2:
        print(json.dumps([], ensure_ascii=False))
        return

    input_cellid = sys.argv[1].strip()
    cell_id_sgi = ''.join(filter(str.isalpha, input_cellid))[:2].upper() + ''.join(filter(str.isdigit, input_cellid)).zfill(5)
    cell_id_giraweb = formatear_cellid(input_cellid)

    # --- Primero buscar en SGI
    token = await obtener_token()
    sgi_result = await consultar_alarmas(token, cell_id_sgi) if token else []

    if sgi_result:
        with open("registros_cellid.json", "w", encoding="utf-8") as f:
            json.dump(sgi_result, f, indent=4, ensure_ascii=False)

        print(json.dumps(sgi_result, ensure_ascii=False))
        return

    # --- Si SGI no devuelve nada, buscar en Giraweb
    solo_letras = ''.join(filter(str.isalpha, input_cellid)).upper()
    gerencia_objetivo = None
    for gerencia, prefijos in prefijos_por_gerencia.items():
        if any(solo_letras.startswith(p) for p in prefijos):
            gerencia_objetivo = gerencia
            break

    if not gerencia_objetivo:
        print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))
        return

    session = requests.Session()
    url = urls_por_gerencia[gerencia_objetivo]
    resultados = buscar_en_gerencia(gerencia_objetivo, url, session, cell_id_giraweb)

    if resultados:
        with open("registros_cellid.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)
        print(json.dumps(resultados, ensure_ascii=False))
    else:
        print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))

# --- Ejecutar ---
if __name__ == "__main__":
    asyncio.run(main())
