# Compilador y Optimizador para Subconjunto de Go (Golang)

Este proyecto es una aplicación web interactiva desarrollada en Python 3.14, que implementa un compilador y optimizador completo para un subconjunto del lenguaje de programación **Go (Golang)**. Utiliza la librería **SLY (Sly Lex Yacc)** para las fases de análisis léxico y sintáctico, y el framework web **FastAPI** para exponer cada fase del pipeline y servir una interfaz gráfica interactiva con soporte de diagramas **Mermaid.js**.

El compilador abarca las 5 etapas canónicas del flujo de compilación:
1. **Análisis Léxico**: Tokenización, reconocimiento de palabras reservadas, operadores, literales y comentarios.
2. **Análisis Sintáctico**: Parser LR con construcción de Árbol de Sintaxis Abstracta (AST) y visualización gráfica.
3. **Análisis Semántico**: Tabla de símbolos con scopes jerárquicos y chequeo estricto de tipos.
4. **Código Intermedio (IR)**: Generación de Three-Address Code (TAC), Triplos, Cuádruplos y notación Postfija (RPN).
5. **Optimización y Grafo de Flujo de Control (CFG)**: Partición en bloques básicos, construcción y métricas de CFG, y aplicación iterativa de 6 técnicas de optimización (Constant Folding, Constant Propagation, CSE, DCE, eliminación de código inalcanzable y simplificación de saltos).

---

## Características del subconjunto de Go soportado

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

*(Si no se tiene un entorno virtual, se puede crear con `uv venv` o `python -m venv .venv`)*

### 2. Instalar dependencias

```bash
python -m pip install -r requirements.txt
# o utilizando uv:
uv sync
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
│   │   ├── routes.py              # Endpoints de la API REST (/tokenize, /parse, /semantic, /ir, /optimize, exports)
│   │   └── schemas.py             # Esquemas Pydantic v2 de las peticiones y respuestas
│   ├── core
│   │   ├── lexer.py               # Analizador léxico (SLY)
│   │   ├── parser.py              # Analizador sintáctico LR y generación de AST (SLY)
│   │   ├── semantic.py            # Análisis semántico, scopes y tabla de símbolos
│   │   ├── ir_generator.py        # Generación de código intermedio (TAC, triplos, cuádruplos, postfijo)
│   │   └── optimizer.py           # Optimización de IR, bloques básicos, CFG y métricas
│   ├── templates
│   │   └── index.html             # Interfaz gráfica web interactiva (SPA)
│   └── main.py                    # Punto de entrada del servidor FastAPI
├── ejemplos
│   ├── aritmetica.ir              # Ejemplo IR aritmético
│   ├── for_loop.ir                # Ejemplo IR bucles
│   ├── if_else.ir                 # Ejemplo IR condicionales
│   └── u3                         # Archivos integradores de optimización Unidad 3
│       ├── ejemplo_integrador.go
│       ├── before.ir
│       └── after.ir
├── pyproject.toml                 # Configuración de dependencias del proyecto
├── README.md                      # Documento principal del repositorio
└── requirements.txt               # Archivo de requerimientos congelados
```
