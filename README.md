# Compilador, Optimizador y Asignador de Registros para Go (Golang)

Este proyecto es una aplicación web interactiva desarrollada en **Python 3.14** que implementa un compilador, optimizador y asignador de registros completo para un subconjunto del lenguaje de programación **Go (Golang)**. 

Utiliza la librería **SLY (Sly Lex Yacc)** para las fases de análisis léxico y sintáctico, **FastAPI** para exponer cada fase del compilador mediante una API REST, **Mermaid.js** para diagramas de Árbol de Sintaxis Abstracta (AST) y Grafos de Flujo de Control (CFG), y **Vis.js Network** para la simulación física interactiva de grafos de interferencia y asignación de registros.

El sistema abarca 6 fases canónicas de compilación:
1. **Análisis Léxico**: Tokenización, reconocimiento de palabras reservadas, operadores, literales, delimitadores y comentarios.
2. **Análisis Sintáctico**: Parser LR con construcción del Árbol de Sintaxis Abstracta (AST) y visualización gráfica.
3. **Análisis Semántico**: Tabla de símbolos jerárquica con resolución de ámbitos (*scopes*) y verificación estricta de tipos.
4. **Código Intermedio (IR)**: Generación de Código de Tres Direcciones (TAC), Triplos, Cuádruplos y notación Postfija (RPN).
5. **Optimización y Grafo de Flujo de Control (CFG / GFG)**: Partición formal en bloques básicos, detección de bloques inalcanzables, cálculo de complejidad ciclomática y aplicación iterativa de 6 técnicas de optimización (*Constant Folding*, propagación de constantes, eliminación de subexpresiones comunes *CSE*, eliminación de código muerto *DCE*, simplificación de saltos y eliminación de código inalcanzable).
6. **Asignación de Registros por Coloración de Grafos de Interferencia**: Parser flexible de listas de adyacencia, cálculo matemático del número cromático mínimo $\chi(G)$ mediante el algoritmo híbrido **DSATUR + Branch & Bound**, asignación a registros de máquina ($R_1, R_2, \dots$) y visualizador dinámico con física de fuerzas en tiempo real.

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

## Interfaz de Usuario Web

La interfaz web está organizada en dos pestañas principales:

1. **Compilador Go**:
   - Editor con numeración de líneas y atajo `Ctrl+Enter`.
   - Pipeline secuencial con botones dedicados: *Análisis léxico*, *Análisis sintáctico*, *Análisis semántico*, *Código intermedio* y *Optimización (GFG / U3)*.
   - Visor interactivo del AST y diagramas comparativos del CFG Original vs CFG Optimizado.
   - Tabla de transformaciones detalladas con justificación técnica por bloque.
   - Comparadores de código TAC e IR (`antes.ir` vs `despues.ir`) con botones de copia y descarga.

2. **Grafo de Interferencia (Asignación de Registros)**:
   - Entrada de texto para listas de adyacencia (formatos admitidos: `A: B, F`, `A: B F`, pares `A-B`, comentarios `#` y nodos aislados).
   - Selector con 7 presets integrados (Ejemplo Guía $A-F$, Ciclo Par $C_6$, Grafo Completo $K_4$, Bipartito $K_{3,3}$, Grafo de Petersen, etc.).
   - Tarjetas de métricas instantáneas ($|V|$ nodos, $|E|$ aristas y certificación de $\chi(G)$).
   - Tarjetas de distribución de colores con el registro asociado ($R_1, R_2, \dots$) y variables asignadas.
   - Tabla detallada colapsable con variable, grado, registro y color.
   - Lienzo interactivo en Vis.js con simulación física, arrastre de nodos, zoom, controles de centrado (*Ajustar*), pausa de física y alternancia de vista coloreada o monocroma.

---

## Instrucciones de Instalación y Ejecución

### 1. Activar el entorno virtual

Desde la raíz del proyecto:

**En Linux / macOS:**
```bash
source .venv/bin/activate
```

**En Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

*(Si no tienes un entorno virtual, créalo con `uv venv` o `python -m venv .venv`)*

### 2. Instalar dependencias

```bash
# Con uv (recomendado):
uv sync

# O con pip:
pip install -r requirements.txt
```

### 3. Iniciar el servidor web

```bash
python app/main.py
```
*El servidor estará disponible de inmediato en: **[http://localhost:8000](http://localhost:8000)***

---

## Suite de Pruebas Unitarias

El proyecto cuenta con una batería de **65 pruebas automatizadas** que validan cada etapa del compilador sin dependencias externas:

```bash
# Ejecutar todas las pruebas (65 tests):
python -m unittest discover tests -v

# O por módulo:
python -m unittest tests/test_lexer_parser.py         # Léxico y Sintáctico (30 tests)
python -m unittest tests/test_semantic.py             # Semántica y Scopes (12 tests)
python -m unittest tests/test_ir.py                   # TAC, Triplos y Cuádruplos (7 tests)
python -m unittest tests/test_optimizer.py            # Bloques y CFG U3 (8 tests)
python -m unittest tests/test_interference_graph.py  # Interferencia y Coloración U4 (8 tests)
```

---

## Estructura del Proyecto

```text
.
├── app/
│   ├── api/
│   │   ├── routes.py              # Endpoints REST (/tokenize, /parse, /semantic, /ir, /optimize, /interference-graph)
│   │   └── schemas.py             # Modelos de validación Pydantic v2
│   ├── core/
│   │   ├── lexer.py               # Analizador léxico (SLY)
│   │   ├── parser.py              # Analizador sintáctico LR y generación de AST (SLY)
│   │   ├── semantic.py            # Análisis semántico, scopes y tabla de símbolos
│   │   ├── ir_generator.py        # Generación de código intermedio (TAC, triplos, cuádruplos, postfijo)
│   │   ├── optimizer.py           # Optimización de IR, bloques básicos, CFG y métricas U3
│   │   └── interference_graph.py  # Grafos de interferencia, DSATUR, Branch & Bound y registros U4
│   ├── templates/
│   │   └── index.html             # Interfaz web SPA (Compilador Go + Visualizador Vis.js)
│   └── main.py                    # Punto de entrada de la aplicación FastAPI
├── tests/                         # Suite de 65 pruebas unitarias con unittest
│   ├── test_lexer_parser.py
│   ├── test_semantic.py
│   ├── test_ir.py
│   ├── test_optimizer.py
│   └── test_interference_graph.py
├── ejemplos/                      # Archivos .go e .ir de demostración y entregables de U3
│   ├── aritmetica.ir
│   ├── for_loop.ir
│   ├── if_else.ir
│   └── u3/
│       ├── ejemplo_integrador.go
│       ├── before.ir
│       └── after.ir
├── AGENTS.md                      # Guía operativa y técnica para agentes de IA
├── current-state.md               # Radiografía exhaustiva del estado técnico del proyecto
├── README.md                      # Este documento
├── pyproject.toml                 # Configuración de dependencias y empaquetado
└── requirements.txt               # Lista de dependencias fijadas
```
