# Analizador Léxico y Sintáctico para Go (Golang)

Este proyecto es una aplicación web interactiva que realiza el **análisis léxico** y **análisis sintáctico** para un subconjunto del lenguaje de programación **Go (Golang)**, utilizando la librería **SLY (Sly Lex Yacc)** y el framework **FastAPI**.

---

## 🚀 Características del Subconjunto de Go (*Mini-Go*)

El analizador soporta un conjunto representativo de la sintaxis de Go:

- **Estructura del Programa**: Declaración de paquete (`package main`) e importaciones (`import "fmt"` / `import ( "fmt" )`).
- **Declaraciones**:
  - Variables explícitas (`var x int = 10`, `var flag bool`)
  - Declaraciones cortas (`x := 20`)
  - Constantes (`const PI float64 = 3.14159`)
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

## 🛠️ Instrucciones para Ejecutar el Proyecto

### 1. Activar el entorno virtual

Desde la raíz del proyecto:

**En Linux / macOS:**
```bash
source .venv/bin/activate
```

**En Windows:**
```cmd
.venv\Scripts\activate
```

*(Si no se tiene un entorno virtual, se puede crear con `python3 -m venv .venv`)*

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Iniciar el servidor

```bash
python app/main.py
```
*O utilizando FastAPI CLI:*
```bash
cd app && fastapi dev main.py
```

### 4. Abrir la interfaz web

Acceda desde su navegador web a:
**[http://localhost:8000](http://localhost:8000)**

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto incluye una suite de pruebas unitarias para validar el funcionamiento del lexer y parser:

```bash
python -m unittest tests/test_lexer_parser.py -v
```

---

## 📁 Estructura del Proyecto

```text
.
├── app/
│   ├── api/
│   │   ├── routes.py      # Endpoints de la API (/tokenize y /parse)
│   │   └── schemas.py     # Esquemas Pydantic para peticiones y respuestas
│   ├── core/
│   │   ├── lexer.py       # Analizador léxico (MyLexer con SLY)
│   │   └── parser.py      # Analizador sintáctico (MyParser con SLY)
│   ├── templates/
│   │   └── index.html     # Interfaz gráfica interactiva
│   └── main.py            # Servidor FastAPI
├── tests/
│   └── test_lexer_parser.py # Suite de pruebas unitarias
├── requirements.txt
└── README.md
```
