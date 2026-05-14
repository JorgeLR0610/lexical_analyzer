# Analizador léxico y sintáctico escrito en Python

Este proyecto es una interfaz web que permite realizar un análisis léxico y sintáctico de bloques de código (basados en Python) utilizando la librería SLY y el framework FastAPI.

## Instrucciones para correr el proyecto

### 1. Activar el entorno virtual (Recomendado)
Abra una terminal en la raíz del proyecto (la carpeta `analizador_lexico`). Si ya se tiene un entorno virtual `.venv`, actívelo con el siguiente comando:

**En Linux / macOS:**
```bash
source .venv/bin/activate
```
**En Windows:**
```cmd
.venv\Scripts\activate
```

*(Si no se tiene un entorno virtual, es posible crear uno ejecutando `python3 -m venv .venv`)*

### 2. Instalar las dependencias
Asegúrese de instalar los requerimientos del proyecto:
```bash
pip install -r requirements.txt
```

### 3. Iniciar el servidor
Navegue hacia el directorio principal de la aplicación (`app`) e inicie el entorno de desarrollo de FastAPI:
```bash
cd app
fastapi dev main.py
```

### 4. Abrir la interfaz
Una vez que el servidor esté en ejecución, abra su navegador web de preferencia y acceda a la siguiente dirección:

**[http://localhost:8000](http://localhost:8000)**
