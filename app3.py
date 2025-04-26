#Versión optimizada que busca directamente en la gerencia correspondiente, filtrando solo alarmas reales y registros cuyo tiempo sea menor a 3 días. Usa requests con ThreadPoolExecutor para acelerar la consulta y BeautifulSoup con lxml para un parsing HTML más rápido y eficiente.

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

# Formatear Cell-ID
def formatear_cellid(cellid):
    letras = ''.join(filter(str.isalpha, cellid)).upper()
    numeros = ''.join(filter(str.isdigit, cellid)).zfill(5)
    return letras + numeros

# Limpiar texto
def limpiar(texto):
    return texto.strip().replace('\n', ' ').replace('\r', '')

# Convertir TIEMPO a días
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

# Leer argumento
if len(sys.argv) < 2:
    print("❌ Debes pasar el Cell-ID como argumento.")
    sys.exit(1)

cell_id_input = sys.argv[1].strip()
cell_id_buscado = formatear_cellid(cell_id_input)

# Detectar el prefijo correcto
prefijo_detectado = None
gerencia_objetivo = None

solo_letras = ''.join(filter(str.isalpha, cell_id_input)).upper()

for gerencia, prefijos in prefijos_por_gerencia.items():
    for prefijo in prefijos:
        if solo_letras.startswith(prefijo):
            prefijo_detectado = prefijo
            gerencia_objetivo = gerencia
            break
    if gerencia_objetivo:
        break

if not gerencia_objetivo:
    print(f"⚠️ No se encontró ninguna gerencia que maneje el prefijo de '{cell_id_input}'")
    sys.exit(0)

print(f"🎯 Buscando Cell-ID '{cell_id_buscado}' en gerencia: {gerencia_objetivo}")

# Columnas a mostrar
column_order = ["site_id", "fecha_creacion", "alarma", "TIEMPO", "cell_owner", "site_name"]

# Función de búsqueda
def buscar_en_gerencia(nombre, url, session):
    try:
        t0 = time.time()
        resp = session.get(url, timeout=8)
        duracion = time.time() - t0
        print(f"🕒 {nombre} respondió en {duracion:.2f} segundos")

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        filas = soup.find_all("tr")
        encontrados = []

        for fila in filas:
            columnas = fila.find_all("td")
            if columnas and len(columnas) == 6:
                cell_id_actual = limpiar(columnas[0].get_text(strip=True)).upper()

                if cell_id_actual == cell_id_buscado:
                    tiempo_texto = limpiar(columnas[-2].get_text(strip=True))

                    # Filtro: solo TIEMPO menor a 3 días
                    if tiempo_en_dias(tiempo_texto) < 3:

                        # Filtro: alarma real (no número de teléfono ni "sin salida")
                        texto_alarma = limpiar(columnas[-1].get_text(strip=True))
                        if not texto_alarma.lower().startswith(("+54", "sin salida", "sms", "whatsapp")):
                            encontrados.append({
                                "site_id": limpiar(columnas[0].get_text(strip=True)),
                                "fecha_creacion": limpiar(columnas[-3].get_text(strip=True)),
                                "alarma": texto_alarma[:120] + "...",
                                "TIEMPO": tiempo_texto,
                                "cell_owner": limpiar(columnas[2].get_text(strip=True)),
                                "site_name": limpiar(columnas[1].get_text(strip=True))
                            })

        return encontrados

    except Exception as e:
        print(f"⚠️ Error en {nombre}: {e}")
        return []

# Ejecutar búsqueda
inicio_total = time.time()
session = requests.Session()
resultados = []

with ThreadPoolExecutor(max_workers=2) as executor:
    url = urls_por_gerencia[gerencia_objetivo]
    futuros = {executor.submit(buscar_en_gerencia, gerencia_objetivo, url, session): gerencia_objetivo}
    for futuro in as_completed(futuros):
        resultado = futuro.result()
        if resultado:
            resultados = resultado
            break

# Mostrar resultados
if resultados:
    tabla_ordenada = [[r[col] for col in column_order] for r in resultados]
    print(tabulate(tabla_ordenada, headers=column_order, tablefmt="grid"))

    with open("registros_cellid.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    print(f"\n⏱ Tiempo total: {time.time() - inicio_total:.2f} segundos")
    print("✅ Archivo actualizado.\n")
    print(json.dumps(resultados, ensure_ascii=False))
else:
    print("⚠️ No se encontró información válida para ese Cell-ID.\n")
    print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))
