#Versión optimizada con asyncio y aiohttp, que reduce tiempos de búsqueda al máximo.
# Usa User-Agent de navegador para evitar bloqueos y filtra resultados directamente durante el scraping, mejorando velocidad y eficiencia.

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import sys
import time

def limpiar(texto):
    return texto.strip().replace('\n', ' ').replace('\r', '')

def formatear_cellid(cellid):
    letras = ''.join(filter(str.isalpha, cellid))[:2].upper()
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

    total_dias = dias + horas/24 + minutos/1440
    return total_dias

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

async def buscar_en_gerencia(session, nombre, url):
    try:
        inicio = time.time()
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        ) as response:

            if response.status != 200:
                print(f"⚠️ Error buscando en {nombre}: HTTP {response.status}")
                return []

            texto = await response.text()
            soup = BeautifulSoup(texto, "html.parser")
            filas = soup.find_all("tr")
            encontrados = []

            for fila in filas:
                columnas = fila.find_all("td")
                if columnas and len(columnas) == 6:
                    cell_id_actual = limpiar(columnas[0].text).upper()
                    if cell_id_actual == cell_id_buscado:
                        tiempo_texto = limpiar(columnas[4].text)
                        if tiempo_en_dias(tiempo_texto) < 3:
                            encontrados.append({
                                "site_id": cell_id_actual,
                                "site_name": limpiar(columnas[1].text),
                                "cell_owner": limpiar(columnas[2].text),
                                "fecha_creacion": limpiar(columnas[3].text),
                                "TIEMPO": tiempo_texto,
                                "alarma": limpiar(columnas[5].text)[:120] + "..."
                            })

            print(f"🔎 {nombre} terminado en {time.time() - inicio:.2f} segundos.")
            return encontrados

    except asyncio.TimeoutError:
        print(f"⚠️ Timeout buscando en {nombre}")
        return []
    except Exception as e:
        print(f"⚠️ Error buscando en {nombre}: {str(e)}")
        return []

async def main():
    inicio_total = time.time()
    async with aiohttp.ClientSession() as session:
        tareas = [buscar_en_gerencia(session, nombre, url) for nombre, url in gerencias.items()]
        resultados_list = await asyncio.gather(*tareas)

        global resultados
        for r in resultados_list:
            if r:
                resultados = r
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
            print("⚠️ No se encontró información para ese Cell-ID o todas superan 3 días.\n")
            print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))

# 🚀 Ejecución adaptada para Python 3.6:
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
