import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import sys

<<<<<<< HEAD
# Mapeo manual de prefijos
prefijos_por_gerencia = {
    "CFBA": ["CF"],
    "PACU": ["ME", "SJ", "SL", "COW", "SC", "CB", "TF", "RN", "NQ"],
    "MED": ["CO", "ST", "SE", "CT", "TU", "JU", "STR", "CTR", "RJ"],
    "LSUR": ["BA", "SF", "CH", "CR", "FO", "MI", "SJ", "ER"],
    "BLAP": ["BA", "PA", "PAR"]
}

# URLs por gerencia
=======
# --- Entradas
cell_id_buscado = sys.argv[1] if len(sys.argv) > 1 else "CF00104"

# --- Configuración
prefijos_por_gerencia = {
    "CFBA": ["CF"],
    "PACU": ["ME", "SJ", "SL", "COW", "SC", "CB", "TF", "RN", "NQ"],
    "MED":  ["CO", "ST", "SE", "CT", "TU", "JU", "STR", "CTR", "RJ"],
    "LSUR": ["BA", "SF", "CH", "CR", "FO", "MI", "SJ", "ER"],
    "BLAP": ["BA", "PA", "PAR"]
}

>>>>>>> 7b447337ddc3ffbfb6d5b9a3dbaad06e7ba4e1fa
urls_por_gerencia = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

<<<<<<< HEAD
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

    with open("registros_cellid.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    # print(f"\n⏱ Tiempo total: {time.time() - inicio_total:.2f} segundos")
    print(json.dumps(resultados, ensure_ascii=False))
else:
    # print("⚠️ No se encontró información válida para ese Cell-ID.\n")
    print(json.dumps({"error": "No se encontró información válida para ese Cell-ID"}, ensure_ascii=False))




# # --- IMPORTS ---
# import warnings
# warnings.filterwarnings("ignore")

# from concurrent.futures import ThreadPoolExecutor, as_completed
# import requests
# from bs4 import BeautifulSoup
# import json
# import time
# import sys

# # --- FUNCIONES AUXILIARES ---
# def limpiar(texto):
#     return texto.strip().replace('\n', ' ').replace('\r', '')

# def formatear_cellid(cellid):
#     letras = ''.join(filter(str.isalpha, cellid))[:2].upper()
#     numeros = ''.join(filter(str.isdigit, cellid)).zfill(5)
#     return letras + numeros

# # --- VALIDAR ARGUMENTOS ---
# if len(sys.argv) < 2:
#     print(json.dumps({"error": "Debes pasar el Cell-ID como argumento."}))
#     sys.exit(1)

# cell_id_buscado = formatear_cellid(sys.argv[1].strip())
# resultados = []

# gerencias = {
#     "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
#     "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
#     "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
#     "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
#     "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
# }

# def buscar_en_gerencia(session, nombre, url):
#     try:
#         response = session.get(url, timeout=5)
#         if response.status_code != 200:
#             return []

#         soup = BeautifulSoup(response.text, "html.parser")
#         filas = soup.find_all("tr")
#         encontrados = []

#         for fila in filas:
#             columnas = fila.find_all("td")
#             if columnas and len(columnas) == 6:
#                 cell_id_actual = limpiar(columnas[0].text).upper()
#                 if cell_id_actual == cell_id_buscado:
#                     encontrados.append({
#                         "site_id": cell_id_actual,
#                         "site_name": limpiar(columnas[1].text),
#                         "cell_owner": limpiar(columnas[2].text),
#                         "fecha_creacion": limpiar(columnas[3].text),
#                         "TIEMPO": limpiar(columnas[4].text),
#                         "alarma": limpiar(columnas[5].text)[:120] + "..."
#                     })
#         return encontrados
#     except Exception as e:
#         return []

# # --- EJECUCIÓN PRINCIPAL ---
# session = requests.Session()
# inicio_total = time.time()

# with ThreadPoolExecutor(max_workers=5) as executor:
#     futuros = {executor.submit(buscar_en_gerencia, session, nombre, url): nombre for nombre, url in gerencias.items()}
#     for futuro in as_completed(futuros):
#         resultados = futuro.result()
#         if resultados:
#             break

# # --- RESPUESTA FINAL ---
# if resultados:
#     print(json.dumps({"resultados": resultados}, ensure_ascii=False))
# else:
#     print(json.dumps({"error": "No se encontró información para ese Cell-ID"}, ensure_ascii=False))


=======
# --- Buscar a qué gerencia pertenece el prefijo
def obtener_gerencia(cell_id):
    for gerencia, prefijos in prefijos_por_gerencia.items():
        for prefijo in prefijos:
            if cell_id.startswith(prefijo):
                return gerencia
    return None

# --- Proceso principal
def buscar_logueo_sin_salida(cell_id):
    gerencia = obtener_gerencia(cell_id)
    if not gerencia:
        print(f"❌ No se encontró una gerencia válida para el Cell-ID '{cell_id}'.")
        return

    url = urls_por_gerencia[gerencia]
    print(f"🌐 Cargando página de logueos para {gerencia}...")

    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        tabla = soup.select_one('div#logueos table.tabla2')
        if not tabla:
            print("❌ No se encontró la tabla de logueos.")
            return

        resultados = []
        rows = tabla.find_all("tr")
        for row in rows:
            columnas = row.find_all("td")
            if len(columnas) >= 5:
                cell = columnas[0].get_text(strip=True)
                salida = columnas[2].get_text(strip=True)

                if cell == cell_id and salida == "Sin salida":
                    resultados.append({
                        "cell_id": cell,
                        "fecha_ingreso": columnas[1].get_text(strip=True),
                        "fecha_salida": salida,
                        "empresa": columnas[3].get_text(strip=True),
                        "contacto": columnas[4].get_text(strip=True),
                    })

        if resultados:
            print("✅ Registro(s) con 'Sin salida' encontrado(s):")
            print(json.dumps(resultados, indent=4, ensure_ascii=False))
        else:
            print(f"⚠️ No se encontraron registros con 'Sin salida' para Cell-ID '{cell_id}'.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al cargar la página: {e}")
>>>>>>> 7b447337ddc3ffbfb6d5b9a3dbaad06e7ba4e1fa

# --- Ejecutar
buscar_logueo_sin_salida(cell_id_buscado)
