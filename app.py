from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import webbrowser
import threading
import os
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Session global compartida para aprovechar conexiones persistentes
session = requests.Session()

# URLs por gerencia
gerencias = {
    "CFBA": "http://10.92.62.254/giraweb/index-tab.php?gerencia=CFBA",
    "PACU": "http://10.92.62.254/giraweb/index-tab.php?gerencia=PACU",
    "MED":  "http://10.92.62.254/giraweb/index-tab.php?gerencia=MED",
    "LSUR": "http://10.92.62.254/giraweb/index-tab.php?gerencia=LSUR",
    "BLAP": "http://10.92.62.254/giraweb/index-tab.php?gerencia=BLAP"
}

column_order = ["CELL-ID", "FECHA", "ALERTA", "TIEMPO", "OWNER", "SITIO"]

@app.route("/")
def index():
    return render_template("index.html")

def buscar_en_gerencia(nombre, url, cell_id_buscado):
    try:
        response = session.get(url, timeout=5)
        if response.status_code != 200:
            return nombre, []

        soup = BeautifulSoup(response.text, "html.parser")
        filas = soup.find_all("tr")
        registros = []

        for fila in filas:
            if cell_id_buscado not in fila.text:
                continue

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

        return nombre, registros

    except Exception as e:
        print(f"❌ Error en {nombre}: {e}")
        return nombre, []

@app.route("/buscar")
def buscar():
    inicio = time.time()
    cell_id_buscado = request.args.get("cellid", "").strip().upper()
    resultados_por_gerencia = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futuros = [executor.submit(buscar_en_gerencia, nombre, url, cell_id_buscado)
                   for nombre, url in gerencias.items()]

        for futuro in futuros:
            nombre, registros = futuro.result()
            if registros:
                resultados_por_gerencia[nombre] = registros

    print(f"⏱ Tiempo total: {time.time() - inicio:.2f} segundos")
    return jsonify(resultados_por_gerencia)

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, abrir_navegador).start()

    app.run(debug=True)
