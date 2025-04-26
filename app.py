#Versión multihilo tradicional que busca en todas las gerencias usando ThreadPoolExecutor con 5 workers. Se destaca por su simplicidad, buena velocidad de respuesta y robustez al combinar requests con filtrado básico durante el scraping.

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import time
import sys

def limpiar(texto):
    return texto.strip().replace('\n', ' ').replace('\r', '')

def formatear_cellid(cellid):
    letras = ''.join(filter(str.isalpha, cellid))[:2].upper()
    numeros = ''.join(filter(str.isdigit, cellid)).zfill(5)
    return letras + numeros

# Leer el argumento
if len(sys.argv) < 2:
    print("❌ Debes pasar el Cell-ID como argumento.")
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

column_order = ["site_id", "fecha_creacion", "alarma", "TIEMPO", "cell_owner", "site_name"]

def buscar_en_gerencia(session, nombre, url):
    try:
        inicio = time.time()
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        filas = soup.find_all("tr")
        encontrados = []

        for fila in filas:
            columnas = fila.find_all("td")
            if columnas and len(columnas) == 6:  # ⚡ Solo procesar filas que tienen 6 columnas (las verdes)
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
        
        print(f"🔎 {nombre} terminado en {time.time() - inicio:.2f} segundos.")
        return encontrados
    except Exception as e:
        print(f"⚠️ Error buscando en {nombre}: {str(e)}")
        return []

# 🕑 Medir tiempo total
inicio_total = time.time()

session = requests.Session()

with ThreadPoolExecutor(max_workers=5) as executor:
    futuros = {executor.submit(buscar_en_gerencia, session, nombre, url): nombre for nombre, url in gerencias.items()}
    for futuro in as_completed(futuros):
        resultados = futuro.result()
        if resultados:
            break

if resultados:
    tabla_ordenada = [[r[col] for col in column_order] for r in resultados]
    print(tabulate(tabla_ordenada, headers=column_order, tablefmt="grid"))

    with open("registros_cellid.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    print(f"\n⏱ Tiempo total: {time.time() - inicio_total:.2f} segundos")
    print("✅ Archivo actualizado.\n")
    print(json.dumps(resultados, ensure_ascii=False))
else:
    print("⚠️ No se encontró información para ese Cell-ID.\n")
    print(json.dumps({"error": "No se encontró información para ese Cell-ID"}, ensure_ascii=False))
