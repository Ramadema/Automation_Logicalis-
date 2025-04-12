import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json

# URLs por gerencia
gerencias = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

# Columnas ordenadas para mostrar
column_order = ["CELL-ID", "FECHA", "ALERTA", "TIEMPO", "OWNER", "SITIO"]

# Bucle principal
while True:
    cell_id_buscado = input("\nIngrese el Cell-ID que desea buscar (o escriba 'salir' para terminar): ").strip().upper()

    if cell_id_buscado.lower() == "salir":
        print("Finalizando el programa.")
        break

    resultados_por_gerencia = {}

    for nombre, url in gerencias.items():
        print(f"🔎 Buscando en {nombre}...", end="")

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"\n❌ No se pudo acceder a {nombre} (código {response.status_code})")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            filas = soup.find_all("tr")
            registros = []

            for fila in filas:
                columnas = fila.find_all("td")
                if columnas and columnas[0].text.strip() == cell_id_buscado:
                    registros.append({
                        "CELL-ID": columnas[0].text.strip(),
                        "FECHA": columnas[-3].text.strip(),
                        "ALERTA": columnas[-1].text.strip()[:120] + "...",
                        "TIEMPO": columnas[-2].text.strip(),
                        "OWNER": columnas[2].text.strip(),
                        "SITIO": columnas[1].text.strip()
                    })

            if registros:
                resultados_por_gerencia[nombre] = registros
                print(" ✅ encontrado.")
                print(f"--- RESULTADOS EN {nombre} ---")
                tabla_ordenada = [[r[col] for col in column_order] for r in registros]
                print(tabulate(tabla_ordenada, headers=column_order, tablefmt="grid"))
                print("\n")
            else:
                print("\r", end="")  # Silencio si no hay resultado

        except requests.RequestException as e:
            print(f"\n❌ Error accediendo a {nombre}: {e}")

    if resultados_por_gerencia:
        with open("registros_cellid.json", "w", encoding="utf-8") as f:
            json.dump({cell_id_buscado: resultados_por_gerencia}, f, indent=4, ensure_ascii=False)

        print("✅ Archivo 'registros_cellid.json' actualizado con los resultados de la búsqueda.\n")
    else:
        print("⚠️ No se encontró información en ninguna gerencia para ese Cell-ID.\n")
