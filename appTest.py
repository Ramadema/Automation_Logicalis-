# --- IMPORTS ---
import warnings
warnings.filterwarnings("ignore")

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import time
import sys

# Mapeo manual de prefijos
prefijos_por_gerencia = {
    "CFBA": ["CF"],
    "PACU": ["ME", "SJ", "SL", "COW", "SC", "CB", "TF", "RN", "NQ"],
    "MED": ["CO", "ST", "SE", "CT", "TU", "JU", "STR", "CTR", "RJ"],
    "LSUR": ["BA", "SF", "CH", "CR", "FO", "MI", "SJ", "ER"],
    "BLAP": ["BA", "PA", "PAR"]
}

# URLs por gerencia
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

# MAIN
if len(sys.argv) < 2:
    print(json.dumps([], ensure_ascii=False))
    sys.exit(1)

cell_id_input = sys.argv[1].strip()
cell_id_buscado = formatear_cellid(cell_id_input)

# Detectar gerencia
solo_letras = ''.join(filter(str.isalpha, cell_id_input)).upper()
gerencia_objetivo = None
for gerencia, prefijos in prefijos_por_gerencia.items():
    if any(solo_letras.startswith(p) for p in prefijos):
        gerencia_objetivo = gerencia
        break

if not gerencia_objetivo:
    print(json.dumps([], ensure_ascii=False))
    sys.exit(0)

def buscar_en_gerencia(nombre, url, session):
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

inicio_total = time.time()
session = requests.Session()
resultados = []

with ThreadPoolExecutor(max_workers=2) as executor:
    url = urls_por_gerencia[gerencia_objetivo]
    futuros = {executor.submit(buscar_en_gerencia, gerencia_objetivo, url, session): gerencia_objetivo}
    for futuro in as_completed(futuros):
        resultados = futuro.result()
        break

# # Solo imprime JSON limpio
# print(json.dumps(resultados, ensure_ascii=False))

# Orden de columnas a mostrar
column_order = ["site_id", "fecha_creacion", "alarma", "TIEMPO", "cell_owner", "site_name"]


if resultados:
    # tabla_ordenada = [[r[col] for col in column_order] for r in resultados]
    # print(tabulate(tabla_ordenada, headers=column_order, tablefmt="grid"))

    # with open("registros_cellid.json", "w", encoding="utf-8") as f:
    #     json.dump(resultados, f, indent=4, ensure_ascii=False)

    # print(f"\n⏱ Tiempo total: {time.time() - inicio_total:.2f} segundos")
    print(json.dumps(resultados, ensure_ascii=False))
else:
    # print("⚠️ No se encontró información válida para ese Cell-ID.\n")
    print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))




# from flask import Flask, render_template, request, jsonify
# import requests
# from bs4 import BeautifulSoup
# import webbrowser
# import threading
# import os
# import time
# from concurrent.futures import ThreadPoolExecutor

# app = Flask(__name__)

# # Session global compartida para aprovechar conexiones persistentes
# session = requests.Session()

# gerencias = {
#     "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
#     "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
#     "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
#     "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
#     "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
# }

# column_order = ["CELL-ID", "FECHA", "ALERTA", "TIEMPO", "OWNER", "SITIO"]

# @app.route("/")
# def index():
#     return render_template("index.html")

# def buscar_en_gerencia(nombre, url, cell_id_buscado):
#     try:
#         response = session.get(url, timeout=5)
#         if response.status_code != 200:
#             return nombre, []

#         soup = BeautifulSoup(response.text, "html.parser")
#         filas = soup.find_all("tr")
#         registros = []

#         for fila in filas:
#             if cell_id_buscado not in fila.text:
#                 continue

#             columnas = fila.find_all("td")
#             if columnas and columnas[0].text.strip() == cell_id_buscado:
#                 registros.append({
#                     "CELL-ID": columnas[0].text.strip(),
#                     "FECHA": columnas[-3].text.strip(),
#                     "ALERTA": columnas[-1].text.strip()[:120] + "...",
#                     "TIEMPO": columnas[-2].text.strip(),
#                     "OWNER": columnas[2].text.strip(),
#                     "SITIO": columnas[1].text.strip()
#                 })

#         return nombre, registros

#     except Exception as e:
#         print(f"❌ Error en {nombre}: {e}")
#         return nombre, []

# @app.route("/buscar")
# def buscar():
#     inicio = time.time()
#     cell_id_buscado = request.args.get("cellid", "").strip().upper()
#     resultados_por_gerencia = {}

#     with ThreadPoolExecutor(max_workers=5) as executor:
#         futuros = [executor.submit(buscar_en_gerencia, nombre, url, cell_id_buscado)
#                    for nombre, url in gerencias.items()]

#         for futuro in futuros:
#             nombre, registros = futuro.result()
#             if registros:
#                 resultados_por_gerencia[nombre] = registros

#     print(f"⏱ Tiempo total: {time.time() - inicio:.2f} segundos")
#     return jsonify(resultados_por_gerencia)

# def abrir_navegador():
#     webbrowser.open_new("http://127.0.0.1:5000/")

# if __name__ == "__main__":
#     if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
#         threading.Timer(1.0, abrir_navegador).start()

#     app.run(debug=True)

