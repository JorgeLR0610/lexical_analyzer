# Analizador Léxico y Sintáctico para Go (Golang)

Este proyecto es una aplicación web interactiva desarrollada en Python, que permite realizar el análisis léxico, sintáctico, semántico y generar una representación intermedia de un bloque de código perteneciente a un subconjunto del lenguaje de programación Go (Golang), utilizando la librería SLY (Sly Lex Yacc) y el framework web FastAPI.

---

## Características del subconjunto de Go

El analizador soporta un conjunto representativo de la sintaxis de Go:

- **Estructura del Programa**: Declaración de paquete (`package main`) e importaciones (`import "fmt"` / `import ( "fmt" )`).
- **Declaraciones**:
  - Variables explícitas (`var x int = 10`, `var bandera bool`)
  - Declaraciones cortas (`x := 20`)
  - Constantes (`const pi float64 = 3.14159`)
  - Definición de tipos y structs (`type Persona struct { nombre string; edad int }`)
- **Funciones**: Definición de funciones con parámetros tipados y valor de retorno (`func sumar(a int, b int) int { return a + b }`).
- **Estructuras de Control**:
  - Condicionales: `if condición { ... } else if { ... } else { ... }`
  - Bucles `for`: Bucles clásicos de 3 cláusulas (`for i := 0; i < n; i++`), bucles condicionales (`for x < 100`) y bucles infinitos (`for { ... }`).
- **Operadores y Expresiones**:
  - Aritméticos: `+`, `-`, `*`, `/`, `%`
  - Relacionales: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Lógicos: `&&`, `||`, `!`
  - Asignaciones e incremento: `:=`, `=`, `+=`, `-=`, `*=`, `/=`, `++`, `--`
- **Literales**: Enteros (`123`), flotantes (`3.14`), cadenas con comillas dobles y raw string literals con backticks, booleanos (`true`, `false`) y `nil`.
- **Comentarios**: De una sola línea (`//...`) y multilínea (`/* ... */`).

---

## Instrucciones para ejecutar el proyecto

### 1. Activar el entorno virtual

Desde la raíz del proyecto:

**En Linux / macOS:**
```bash
source .venv/bin/activate
```

**En Windows (Powershell):**
```cmd
.venv\Scripts\Activate.ps1
```

*(Si no se tiene un entorno virtual, se puede crear con `python -m venv .venv`)*

### 2. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 3. Iniciar el servidor

```bash
python app/main.py
```

### 4. Abrir la interfaz web

Acceda desde su navegador web a:
**[http://localhost:8000](http://localhost:8000)**

---

## Estructura del Proyecto

```text
.
├── app
│   ├── api
│   │   ├── routes.py              # Endpoints de la API
│   │   └── schemas.py             # Esquemas Pydantic de las peticiones y respuestas
│   ├── core
│   │   ├── ir_generator.py        # Generación de código intermedio
│   │   ├── lexer.py               # Analizador léxico
│   │   ├── parser.py              # Analizador sintáctico
│   │   └── semantic.py            # Análisis semántico
│   ├── main.py                    # Punto de entrada del programa
│   └── templates
│       └── index.html             # Interfaz gráfica web
├── README.md
├── requirements.txt               # Archivo de requerimientos para correr el programa
```
