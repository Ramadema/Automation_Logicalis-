import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import os
import time
import sys

# Verificar argumento recibido
if len(sys.argv) < 2:
    print("❌ Debes pasar el Cell-ID como argumento.")
    sys.exit(1)

cell_id_buscado = sys.argv[1].strip().upper()
resultados = []

# URLs por gerencia
gerencias = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

column_order = ["site_id", "fecha_creacion", "alarma", "TIEMPO", "cell_owner", "site_name"]

for nombre, url in gerencias.items():
    inicio = time.time()
    print(f"🔎 Buscando en {nombre}...", end="")

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"\n❌ No se pudo acceder a {nombre} (código {response.status_code})")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        filas = soup.find_all("tr")

        for fila in filas:
            columnas = fila.find_all("td")
            if columnas and columnas[0].text.strip() == cell_id_buscado:
                resultados.append({
                    "site_id": columnas[0].text.strip(),
                    "fecha_creacion": columnas[-3].text.strip(),
                    "alarma": columnas[-1].text.strip()[:120] + "...",
                    "TIEMPO": columnas[-2].text.strip(),
                    "cell_owner": columnas[2].text.strip(),
                    "site_name": columnas[1].text.strip()
                })

        if resultados:
            print(" ✅ encontrado.")
            tabla_ordenada = [[r[col] for col in column_order] for r in resultados]
            print(tabulate(tabla_ordenada, headers=column_order, tablefmt="grid"))
            break
        else:
            print(" ❌ No encontrado en", nombre)

    except requests.RequestException as e:
        print(f"\n❌ Error accediendo a {nombre}: {e}")

if resultados:
    with open("registros_cellid.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    print(f"⏱ Tiempo total: {time.time() - inicio:.2f} segundos")
    print("✅ Archivo actualizado.\n")

    # ⬇️ Esta línea es la que necesita Flask para generar el guardado del json
    print(json.dumps(resultados, ensure_ascii=False))
else:
    print("⚠️ No se encontró información para ese Cell-ID.\n")
    print(json.dumps({"error": "No se encontró información para ese Cell-ID"}, ensure_ascii=False))