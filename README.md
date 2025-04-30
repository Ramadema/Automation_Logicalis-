

---

## Instalación local de pip y librerías necesarias (sin permisos de administrador)

Este proyecto requiere algunas librerías externas de Python (`requests`, `beautifulsoup4`, `tabulate`). Si no tenés `pip` instalado o no contás con permisos de administrador, seguí estos pasos para instalar todo **localmente**.

---

### ✅ 1. Instalar pip localmente

1. Descargá el archivo `get-pip.py` desde el sitio oficial:  
   [https://bootstrap.pypa.io/get-pip.py](https://bootstrap.pypa.io/get-pip.py)

2. Guardalo en la carpeta del proyecto o en cualquier ubicación donde tengas permisos.

3. Abrí una terminal (PowerShell o CMD) en esa carpeta y ejecutá:

   ```bash
   python get-pip.py --user
   ```

   > Esto instalará `pip` en tu entorno local sin requerir privilegios de administrador.

---

### ✅ 2. Instalar las librerías necesarias

Una vez instalado `pip`, ejecutá el siguiente comando para instalar las dependencias del proyecto:

```bash
python -m pip install --user -r requirements.txt
```

Estas librerías permiten:
- `requests`: realizar peticiones HTTP
- `beautifulsoup4`: analizar contenido HTML
- `tabulate`: mostrar tablas en consola de forma estética

---

### ✅ 3. Verificar que todo esté correcto

Podés verificar que las librerías se instalaron correctamente con:

```bash
python -c "import requests, bs4, tabulate; print('Todo instalado correctamente')"
```

---

### 💡 Tip opcional

Para usar `pip` directamente en terminal (sin `python -m`), agregá esta carpeta a tu `PATH`:

```
C:\Users\TU_USUARIO\.local\bin
```

---

> Si tenés cualquier duda sobre la instalación, podés abrir un issue o consultarme a mi sin drama 

> Se pienza agregar una salida completa por json.
> Aplicacion de WILAB sobre la appProdu
