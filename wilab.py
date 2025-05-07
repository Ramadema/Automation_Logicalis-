import asyncio
import aiohttp
import json
import sys
import time
import ssl

def formatear_cellid(cellid):
    letras = ''.join(filter(str.isalpha, cellid))[:2].upper()
    numeros = ''.join(filter(str.isdigit, cellid)).zfill(5)
    return letras + numeros

# Verificar argumento
if len(sys.argv) < 2:
    print(json.dumps([], ensure_ascii=False))
    sys.exit(1)

cell_id = formatear_cellid(sys.argv[1].strip())

LOGIN_URL = "https://sgi.claro.amx/auth/local"
GRAPHQL_URL = "https://sgi.claro.amx/api/graphql"

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Origin": "https://sgi.claro.amx",
    "Accept": "application/json"
}

LOGIN_CREDENCIALES = {
    "username": "EXA53410",
    "password": "Agosto.12"
}

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

QUERY = """
query EVENTS_AND_DEVICES($client_id: String!) {
  events: events_by_client_id(client_id: $client_id) {
    site {
      name
    }
    device {
      description {
        model
      }
    }
    name
    ts
    severity
    message
  }
}
"""

async def obtener_token():
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), headers=HEADERS_BASE) as session:
        try:
            async with session.post(LOGIN_URL, json=LOGIN_CREDENCIALES) as resp:
                if resp.status != 200:
                    print("❌ Falló el login.")
                    print(await resp.text())
                    return None
                data = await resp.json()
                return data.get("token")
        except Exception as e:
            print(f"❌ Excepción durante login: {e}")
            return None

async def consultar_alarmas(token, cell_id):
    headers = {
        **HEADERS_BASE,
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "operationName": "EVENTS_AND_DEVICES",
        "query": QUERY,
        "variables": {
            "client_id": cell_id
        }
    }

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), headers=headers) as session:
        try:
            async with session.post(GRAPHQL_URL, json=payload) as response:
                if response.status != 200:
                    print("❌ Error GraphQL:")
                    print(await response.text())
                    return []

                data = await response.json()
                eventos = data.get("data", {}).get("events", [])
                resultados = []

                for e in eventos:
                    resultado = {
                        "site_name": e.get("site", {}).get("name"),
                        "device_model": e.get("device", {}).get("description", {}).get("model"),
                        "event_name": e.get("name"),
                        "alarma": e.get("message"),
                        "severity": e.get("severity"),
                        "fecha_creacion": e.get("ts")
                    }
                    if all(resultado.values()):
                        resultados.append(resultado)

                return resultados

        except Exception as e:
            print(f"❌ Excepción en GraphQL: {e}")
            return []

async def main():
    inicio = time.time()
    token = await obtener_token()
    if not token:
        print("❌ No se pudo obtener el token.")
        return

    resultado = await consultar_alarmas(token, cell_id)

    if resultado:
        with open("registros_cellid.json", "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=4, ensure_ascii=False)

        print(json.dumps(resultado, ensure_ascii=False))
    else:
        print("⚠️ No se encontraron alarmas o hubo un error.")
        print(json.dumps([], ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
