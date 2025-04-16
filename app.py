import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import os
import time

# URLs por gerencia
gerencias = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

# Columnas ordenadas para mostrar
column_order = ["site_id", "fecha_creacion", "alarma", "TIEMPO", "cell_owner", "site_name"]

# Borro el contenido del archivo JSON al iniciar
with open("registros_cellid.json", "w", encoding="utf-8") as f:
    json.dump([], f)

# Menú principal
def mostrar_menu():
    print("=== MENÚ PRINCIPAL ===")
    print("1. Estado del Sitio (buscar Cell-ID)")
    print("2. Salir")

# Bucle principal del menú
while True:
    os.system('cls' if os.name == 'nt' else 'clear')
    mostrar_menu()
    opcion = input("Seleccione una opción: ").strip()
    os.system('cls' if os.name == 'nt' else 'clear')

    if opcion == "2":
        print("Finalizando el programa.")
        break
    elif opcion != "1":
        print("❌ Opción no válida. Intente de nuevo.\n")
        continue

    # Si eligió opción 1
    cell_id_buscado = input("\nIngrese el Cell-ID que desea buscar: ").strip().upper()
    resultados = []

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
                print(f"--- RESULTADOS EN {nombre} ---")
                tabla_ordenada = [[r[col] for col in column_order] for r in resultados]
                print(tabulate(tabla_ordenada, headers=column_order, tablefmt="grid"))
                print("\n")
                break  
            else:
                print("\r", end="")

        except requests.RequestException as e:
            print(f"\n❌ Error accediendo a {nombre}: {e}")

    if resultados:
        with open("registros_cellid.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)

        print(f"⏱ Tiempo total: {time.time() - inicio:.2f} segundos")
        print("✅ Archivo 'registros_cellid.json' actualizado con los resultados de la búsqueda.\n")
        input("⬇️​Presione enter para continuar con el menu⬇️​")
    else:
        print("⚠️ No se encontró información para ese Cell-ID.\n")
