# -*- coding: utf-8 -*-
# appProd_fast.py  (compatible Python 3.6 / aiohttp 3.0.1)

import os
import sys
import json
import ssl
import time
import asyncio
import aiohttp
from lxml import html as lxml_html
from pathlib import Path

# --- Compatibilidad con aiohttp viejo (3.0.1 no trae ClientTimeout)
try:
    from aiohttp import ClientTimeout
    HAS_CLIENT_TIMEOUT = True
except Exception:
    ClientTimeout = None
    HAS_CLIENT_TIMEOUT = False

# -------------------- CONFIG GLOBAL -------------------- #
LOGIN_URL = "https://sgi.claro.amx/auth/local"
GRAPHQL_URL = "https://sgi.claro.amx/api/graphql"

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Origin": "https://sgi.claro.amx",
    "Accept": "application/json",
}

# Mover credenciales a variables de entorno si es posible
LOGIN_CREDENCIALES = {
    "username": os.getenv("SGI_USER", "EXA53410"),
    "password": os.getenv("SGI_PASS", "Agosto.23*"),
}

# Ignorar validación SSL (entorno interno)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Timeouts (en 3.0.1 se pasa como float/int)
if HAS_CLIENT_TIMEOUT:
    TIMEOUT_SGI = ClientTimeout(total=12)
    TIMEOUT_GIRA = ClientTimeout(total=12)
else:
    TIMEOUT_SGI = 12
    TIMEOUT_GIRA = 12

def timeout_kwargs(value):
    return {"timeout": value}

# Cache de HTML en disco (por gerencia). TTL en segundos
GIRA_CACHE_TTL = int(os.getenv("GIRA_CACHE_TTL", "600"))
CACHE_DIR = Path(os.getenv("GIRA_CACHE_DIR", "/tmp"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Ventana de gracia para preferir SGI aunque Giraweb termine primero (ms)
SGI_GRACE_MS = int(os.getenv("SGI_GRACE_MS", "1200"))

QUERY = """
query EVENTS_AND_DEVICES($client_id: String!) {
  events: events_by_client_id(client_id: $client_id) {
    site { name }
    device { description { model } }
    name
    ts
    severity
    message
  }
}
"""

# -------------------- RUTEO POR GERENCIA -------------------- #
# Incluye Argentina, Uruguay (URUG) y Paraguay (PARA)
prefijos_por_gerencia = {
    # Argentina
    "CFBA": ["CF"],
    "PACU": ["ME", "SJ", "SL", "COW", "SC", "CB", "TF", "RN", "NQ"],
    "MED":  ["CO", "ST", "SE", "CT", "TU", "JU", "STR", "CTR", "RJ"],
    "LSUR": ["BA", "SF", "CH", "CR", "FO", "MI", "SJ", "ER"],
    "BLAP": ["BA", "PA", "PAR"],

    # Uruguay
    "URUG": ["MO", "PY", "SO", "AR", "MA", "RO", "LA", "TT", "TA", "CA"],

    # Paraguay
    "PARA": ["CG", "AM", "PG", "MS", "AP", "CI", "NE", "CZ", "CP", "IT", "SP", "GU", "PH", "CD", "AS", "BO"]
}

urls_por_gerencia = {
    # Argentina
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP",

    # Uruguay y Paraguay
    "URUG": "http://10.92.62.254/giraweb/index-tab.php?gerencia=URUG",
    "PARA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PARA"
}

# -------------------- HELPERS -------------------- #
def limpiar(s):
    if s is None:
        return ""
    return " ".join(s.replace("\r", " ").replace("\n", " ").split()).strip()

def formatear_cellid(cellid):
    letras = "".join(ch for ch in cellid if ch.isalpha()).upper()
    numeros = "".join(ch for ch in cellid if ch.isdigit()).zfill(5)
    return letras + numeros

def cellid_para_sgi(cellid):
    letras = "".join(ch for ch in cellid if ch.isalpha())[:2].upper()
    numeros = "".join(ch for ch in cellid if ch.isdigit()).zfill(5)
    return letras + numeros

def tiempo_en_dias(tiempo_texto):
    if not tiempo_texto:
        return 9999.0
    dias = horas = minutos = 0
    parts = tiempo_texto.split()
    for i, p in enumerate(parts):
        if p == "d":
            dias = int(parts[i - 1]) if i > 0 and parts[i - 1].isdigit() else 0
        elif p == "h":
            horas = int(parts[i - 1]) if i > 0 and parts[i - 1].isdigit() else 0
        elif p == "m":
            minutos = int(parts[i - 1]) if i > 0 and parts[i - 1].isdigit() else 0
    return dias + horas / 24.0 + minutos / 1440.0

def es_fila_alarma_valida_from_texts(texts):
    """
    Valida filas de la tabla de Alarmas para excluir entradas de Logueos/Contacto.
    Requiere al menos 6 columnas. Filtra última columna si comienza con:
    +54 (AR), +598 (UY), +595 (PY), 'sin salida', 'sms', 'whatsapp'.
    """
    if len(texts) < 6:
        return False
    site_id = limpiar(texts[0]).upper()
    last_col = limpiar(texts[-1]).lower()
    if not (site_id.isalnum() and any(c.isalpha() for c in site_id) and any(c.isdigit() for c in site_id)):
        return False
    if last_col.startswith(("+54", "+598", "+595", "sin salida", "sms", "whatsapp")):
        return False
    return True

def detectar_gerencia_por_prefijo(cellid_letras):
    for ger, prefijos in prefijos_por_gerencia.items():
        for p in prefijos:
            if cellid_letras.startswith(p):
                return ger
    return None

# -------------------- HTTP (con retries/backoff) -------------------- #
async def fetch_with_retries(session, url, timeout_value, retries=2):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            async with session.get(url, **timeout_kwargs(timeout_value)) as resp:
                if resp.status != 200:
                    last_exc = RuntimeError("HTTP %s" % resp.status)
                else:
                    return await resp.text()
        except Exception as e:
            last_exc = e
        if attempt < retries:
            await asyncio.sleep(0.4 * (2 ** attempt))
    print(u"⚠️  fetch error %s: %s" % (url, last_exc), file=sys.stderr)
    return None

def cache_path_for_gerencia(gerencia):
    return CACHE_DIR / ("giraweb_cache_%s.html" % gerencia)

def load_cache_if_fresh(gerencia, ttl_sec):
    p = cache_path_for_gerencia(gerencia)
    if not p.exists():
        return None
    try:
        age = time.time() - p.stat().st_mtime
        if age <= ttl_sec:
            return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    return None

def save_cache(gerencia, html_text):
    p = cache_path_for_gerencia(gerencia)
    try:
        p.write_text(html_text, encoding="utf-8", errors="ignore")
    except Exception:
        pass

def make_session_sgi():
    kwargs = dict(connector=aiohttp.TCPConnector(ssl=ssl_context, limit=20, keepalive_timeout=15),
                  headers=HEADERS_BASE)
    if HAS_CLIENT_TIMEOUT:
        kwargs["timeout"] = TIMEOUT_SGI
    return aiohttp.ClientSession(**kwargs)

def make_session_gira():
    kwargs = dict(connector=aiohttp.TCPConnector(ssl=False, limit=10, keepalive_timeout=15))
    if HAS_CLIENT_TIMEOUT:
        kwargs["timeout"] = TIMEOUT_GIRA
    return aiohttp.ClientSession(**kwargs)

# -------------------- SGI (async) -------------------- #
async def sgi_query(cell_id_sgi):
    async with make_session_sgi() as session:
        # Login
        try:
            async with session.post(LOGIN_URL, json=LOGIN_CREDENCIALES, **timeout_kwargs(TIMEOUT_SGI)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                token = data.get("token")
                if not token:
                    return []
        except Exception:
            return []

        # GraphQL
        headers = dict(HEADERS_BASE)
        headers["Authorization"] = "Bearer %s" % token
        payload = {
            "operationName": "EVENTS_AND_DEVICES",
            "query": QUERY,
            "variables": {"client_id": cell_id_sgi},
        }
        try:
            async with session.post(GRAPHQL_URL, json=payload, headers=headers, **timeout_kwargs(TIMEOUT_SGI)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
        except Exception:
            return []

        eventos = (data or {}).get("data", {}).get("events", []) or []
        out = []
        for e in eventos:
            site = (e or {}).get("site") or {}
            device = (e or {}).get("device") or {}
            desc = device.get("description") or {}
            item = {
                "site_name": site.get("name"),
                "device_model": desc.get("model"),
                "event_name": (e or {}).get("name"),
                "alarma": (e or {}).get("message"),
                "severity": (e or {}).get("severity"),
                "fecha_creacion": (e or {}).get("ts"),
            }
            if all(item.values()):
                out.append(item)
        return out

# -------------------- Giraweb (async fetch + lxml parse) -------------------- #
def parse_giraweb(html_text, cell_id_buscado):
    """
    Devuelve (resultados_alarmas, datos_oos)
    """
    if not html_text:
        return [], []

    tree = lxml_html.fromstring(html_text)

    # 1) Alarmas
    resultados = []
    rows = tree.xpath("//tr[td]")
    for row in rows:
        cols = row.xpath("./td")
        texts = [limpiar(col.text_content()) for col in cols]
        if not es_fila_alarma_valida_from_texts(texts):
            continue

        site_id = texts[0].upper()
        if site_id != cell_id_buscado:
            continue

        try:
            tiempo_texto = texts[-2]
            if tiempo_en_dias(tiempo_texto) < 3.0:
                alarma_txt = texts[-1]
                if len(alarma_txt) > 120:
                    alarma_txt = alarma_txt[:120] + "..."
                resultado = {
                    "site_id": site_id,
                    "fecha_creacion": texts[-3],
                    "alarma": alarma_txt,
                    "TIEMPO": tiempo_texto,
                    "cell_owner": texts[2] if len(texts) > 2 else "",
                    "site_name": texts[1] if len(texts) > 1 else "",
                }
                if all(limpiar(str(v)) for v in resultado.values()):
                    resultados.append(resultado)
        except Exception:
            continue

    # 2) OOS en tabla class="tabla2"
    datos_oos = []
    tablas_oos = tree.xpath('//table[contains(@class,"tabla2")]')
    if tablas_oos:
        tabla = tablas_oos[0]
        dentro_de_oos = False
        for row in tabla.xpath(".//tr"):
            cols = row.xpath("./td")
            texts = [limpiar(col.text_content()) for col in cols]
            if not texts or all(t == "" for t in texts):
                continue

            if len(texts) >= 13:
                cell_id_actual = (texts[0] or "").upper()
                if cell_id_actual != cell_id_buscado:
                    dentro_de_oos = False
                    continue
                dentro_de_oos = True
                tec = texts[10] if len(texts) > 10 else ""
                fecha = texts[12] if len(texts) > 12 else ""
                if tec and fecha:
                    datos_oos.append({"TEC": tec, "fecha_creacion_tec": fecha})

            elif dentro_de_oos and len(texts) == 3:
                tec = texts[0]
                fecha = texts[2]
                if tec and fecha:
                    datos_oos.append({"TEC": tec, "fecha_creacion_tec": fecha})

    return resultados, datos_oos

async def giraweb_flow(gerencia, url, cell_id_buscado):
    # Cache
    html_text = None
    if GIRA_CACHE_TTL > 0:
        cached = load_cache_if_fresh(gerencia, GIRA_CACHE_TTL)
        if cached is not None:
            html_text = cached

    if html_text is None:
        async with make_session_gira() as session:
            html_text = await fetch_with_retries(session, url, TIMEOUT_GIRA, retries=2)
        if not html_text:
            return None
        if GIRA_CACHE_TTL > 0:
            save_cache(gerencia, html_text)

    resultados, datos_oos = parse_giraweb(html_text, cell_id_buscado)
    salida = list(resultados) if resultados else []
    if datos_oos:
        salida.append({"sitios_oos": datos_oos})
    return {"salida": salida}

# -------------------- MAIN COORDINADOR -------------------- #
async def main():
    if len(sys.argv) < 2:
        print(json.dumps([], ensure_ascii=False))
        return

    input_cellid = sys.argv[1].strip()
    cell_id_sgi = cellid_para_sgi(input_cellid)
    cell_id_giraweb = formatear_cellid(input_cellid)

    solo_letras = "".join(ch for ch in input_cellid if ch.isalpha()).upper()
    gerencia_objetivo = detectar_gerencia_por_prefijo(solo_letras)
    if not gerencia_objetivo:
        print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))
        return
    url_gira = urls_por_gerencia[gerencia_objetivo]

    # Disparamos SGI y Giraweb en paralelo
    sgi_task = asyncio.ensure_future(sgi_query(cell_id_sgi))
    gira_task = asyncio.ensure_future(giraweb_flow(gerencia_objetivo, url_gira, cell_id_giraweb))

    done, pending = await asyncio.wait({sgi_task, gira_task}, return_when=asyncio.FIRST_COMPLETED)

    # Caso 1: SGI terminó primero y trae datos -> cancelar Giraweb y devolver SGI
    if sgi_task in done:
        sgi_result = sgi_task.result() or []
        if sgi_result:
            if not gira_task.done():
                gira_task.cancel()
                try:
                    await gira_task
                except asyncio.CancelledError:
                    pass
            try:
                Path("registros_cellid.json").write_text(
                    json.dumps(sgi_result, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass
            print(json.dumps(sgi_result, ensure_ascii=False))
            return

    # Caso 2: Giraweb terminó primero -> esperar breve GRACE por SGI para preferirlo si llega con datos
    if gira_task in done and sgi_task not in done and SGI_GRACE_MS > 0:
        try:
            await asyncio.wait({sgi_task}, timeout=SGI_GRACE_MS / 1000.0)
        except Exception:
            pass

    # Si SGI ya respondió ahora con datos, usarlo
    if sgi_task.done():
        try:
            sgi_result = sgi_task.result() or []
        except Exception:
            sgi_result = []
        if sgi_result:
            # cancelar gira si sigue corriendo
            if not gira_task.done():
                gira_task.cancel()
                try:
                    await gira_task
                except asyncio.CancelledError:
                    pass
            try:
                Path("registros_cellid.json").write_text(
                    json.dumps(sgi_result, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except Exception:
                pass
            print(json.dumps(sgi_result, ensure_ascii=False))
            return

    # Caso 3: usar Giraweb
    if not gira_task.done():
        try:
            gira_res = await gira_task
        except asyncio.CancelledError:
            gira_res = None
    else:
        gira_res = gira_task.result()

    salida = (gira_res or {}).get("salida") if gira_res else None
    if salida:
        try:
            Path("registros_cellid.json").write_text(
                json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass
        print(json.dumps(salida, ensure_ascii=False))
    else:
        print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))

# --- RUN ---
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
