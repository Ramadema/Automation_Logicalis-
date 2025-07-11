import requests
from bs4 import BeautifulSoup
import json
import sys

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

urls_por_gerencia = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

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

# --- Ejecutar
buscar_logueo_sin_salida(cell_id_buscado)
