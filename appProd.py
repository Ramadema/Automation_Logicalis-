# --- IMPORTS ---
import warnings
warnings.filterwarnings("ignore")

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import json
import time
import sys

# --- FUNCIONES AUXILIARES ---
def limpiar(texto):
    return texto.strip().replace('\n', ' ').replace('\r', '')

def formatear_cellid(cellid):
    letras = ''.join(filter(str.isalpha, cellid))[:2].upper()
    numeros = ''.join(filter(str.isdigit, cellid)).zfill(5)
    return letras + numeros

# --- VALIDAR ARGUMENTOS ---
if len(sys.argv) < 2:
    print(json.dumps({"error": "Debes pasar el Cell-ID como argumento."}))
    sys.exit(1)

cell_id_buscado = formatear_cellid(sys.argv[1].strip())
resultados = []

gerencias = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

def buscar_en_gerencia(session, nombre, url):
    try:
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        filas = soup.find_all("tr")
        encontrados = []

        for fila in filas:
            columnas = fila.find_all("td")
            if columnas and len(columnas) == 6:
                cell_id_actual = limpiar(columnas[0].text).upper()
                if cell_id_actual == cell_id_buscado:
                    encontrados.append({
                        "site_id": cell_id_actual,
                        "site_name": limpiar(columnas[1].text),
                        "cell_owner": limpiar(columnas[2].text),
                        "fecha_creacion": limpiar(columnas[3].text),
                        "TIEMPO": limpiar(columnas[4].text),
                        "alarma": limpiar(columnas[5].text)[:120] + "..."
                    })
        return encontrados
    except Exception as e:
        return []

# --- EJECUCIÓN PRINCIPAL ---
session = requests.Session()
inicio_total = time.time()

with ThreadPoolExecutor(max_workers=5) as executor:
    futuros = {executor.submit(buscar_en_gerencia, session, nombre, url): nombre for nombre, url in gerencias.items()}
    for futuro in as_completed(futuros):
        resultados = futuro.result()
        if resultados:
            break

# --- RESPUESTA FINAL ---
if resultados:
    print(json.dumps({"resultados": resultados}, ensure_ascii=False))
else:
    print(json.dumps({"error": "No se encontró información para ese Cell-ID"}, ensure_ascii=False))


