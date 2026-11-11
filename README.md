# Compilador, optimizador y asignador de registros para Go (Golang)

Este proyecto es una aplicación web interactiva desarrollada en **Python 3.14** que implementa un compilador, optimizador y asignador de registros completo para un subconjunto del lenguaje de programación **Go (Golang)**. 

Utiliza la librería **SLY (Sly Lex Yacc)** para las fases de análisis léxico y sintáctico, **FastAPI** para exponer cada fase del compilador mediante una API REST, **Mermaid.js** para diagramas de Árbol de Sintaxis Abstracta (AST) y Grafos de Flujo de Control (CFG), y **Vis.js Network** para la simulación física interactiva de grafos de interferencia y asignación de registros.

El sistema abarca 7 fases de compilación:
1. **Análisis Léxico**: Tokenización, reconocimiento de palabras reservadas, operadores, literales, delimitadores y comentarios.
2. **Análisis Sintáctico**: Parser LR con construcción del Árbol de Sintaxis Abstracta (AST) y visualización gráfica.
3. **Análisis Semántico**: Tabla de símbolos jerárquica con resolución de ámbitos (*scopes*) y verificación estricta de tipos.
4. **Código Intermedio (IR)**: Generación de Código de Tres Direcciones (TAC), Triplos, Cuádruplos y notación Postfija (RPN).
5. **Optimización y Grafo de Flujo de Control (CFG / GFG)**: Partición formal en bloques básicos, detección de bloques inalcanzables, cálculo de complejidad ciclomática y aplicación iterativa de 6 técnicas de optimización (*Constant Folding*, propagación de constantes, eliminación de subexpresiones comunes *CSE*, eliminación de código muerto *DCE*, simplificación de saltos y eliminación de código inalcanzable).
6. **Asignación de Registros por Coloración de Grafos de Interferencia**: Parser flexible de listas de adyacencia, cálculo matemático del número cromático mínimo $\chi(G)$ mediante el algoritmo híbrido **DSATUR + Branch & Bound**, asignación a registros de máquina ($R_1, R_2, \dots$) y visualizador dinámico con física de fuerzas.
7. **Generación de Código Objeto**: Generación de código ensamblador ejecutable para arquitectura **x86-64 Linux** utilizando **GNU Assembler** con sintaxis Intel (`.intel_syntax noprefix`), análisis de vida de variables, asignación de registros (`rbx`, `r12`-`r15`), gestión de derrames a pila (*spilling*), alineación del marco según System V AMD64 ABI y verificación en tiempo de ejecución.

---

## Características del subconjunto de Go soportado

- **Estructura del programa**: Declaración de paquete (`package main`) e importaciones (`import "fmt"` / `import ( "fmt" )`).
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
- **Literales**: Enteros (`123`), flotantes (`3.14`), cadenas con comillas dobles y string literales con backticks, booleanos (`true`, `false`) y `nil`.
- **Comentarios**: De una sola línea (`//...`) y multilínea (`/* ... */`).

---

## Interfaz de Usuario Web

La interfaz web está organizada en dos pestañas principales:

1. **Compilador Go**:
   - Editor con numeración de líneas y atajo `Ctrl+Enter`.
   - Botones dedicados: *Análisis léxico*, *Análisis sintáctico*, *Análisis semántico*, *Código intermedio*, *Optimización* y *Código objeto*.
   - Visor interactivo del AST y diagramas comparativos del CFG Original vs CFG Optimizado.
   - Tabla de transformaciones detalladas con justificación técnica por bloque.
   - Comparadores de código TAC e IR (`antes.ir` vs `despues.ir`) con botones de copia y descarga.
   - Panel de **Código Objeto** con visor de código ensamblador x86-64 Intel, descarga directa de `programa.asm`, tabla completa de asignación de registros y derrames con descarga de `registros.csv`, y guía de comandos para compilación nativa en Linux.

2. **Grafo de interferencia (asignación de registros)**:
   - Entrada de texto para listas de adyacencia (formatos admitidos: `A: B, F`, `A: B F`, pares `A-B`, comentarios `#` y nodos aislados).
   - Selector con 7 ejemplos integrados (Ejemplo Guía $A-F$, Ciclo Par $C_6$, Grafo Completo $K_4$, Bipartito $K_{3,3}$, Grafo de Petersen, etc.).
   - Tarjetas de métricas instantáneas ($|V|$ nodos, $|E|$ aristas y certificación de $\chi(G)$).
   - Tarjetas de distribución de colores con el registro asociado ($R_1, R_2, \dots$) y variables asignadas.
   - Tabla detallada colapsable con variable, grado, registro y color.
   - Lienzo interactivo en Vis.js con simulación física, arrastre de nodos, zoom, controles de centrado (*Botón Ajustar*), pausa de física y alternancia de vista coloreada o monocromática.

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

*(Si no se tiene un entorno virtual, crearlo con  `python -m venv .venv`)*

### 2. Instalar dependencias

```bash
# Con pip:
pip install -r requirements.txt
```

### 3. Iniciar el servidor web

```bash
python app/main.py
```
*El servidor estará disponible de inmediato en: **[http://localhost:8000](http://localhost:8000)***

---

## Compilación y ejecución del código objeto en Linux x86-64

El código ensamblador emitido por el compilador utiliza la sintaxis Intel de GNU Assembler (`.intel_syntax noprefix`) y la convención de llamadas System V AMD64 ABI.

Para ensamblar y ejecutar el archivo `programa.asm` generado:

```bash
# 1. Ensamblar con GNU Assembler (a través de GCC):
gcc -x assembler -c programa.asm -o programa.o

# 2. Enlazar con la biblioteca estándar de C:
gcc programa.o -o programa

# 3. Ejecutar el binario:
./programa
```
---

## Estructura del Proyecto

```text
.
├── app/
│   ├── api/
│   │   ├── routes.py              # Endpoints REST
│   │   └── schemas.py             # Modelos de validación Pydantic
│   ├── core/
│   │   ├── lexer.py               # Analizador léxico (SLY)
│   │   ├── parser.py              # Analizador sintáctico LR y generación de AST (SLY)
│   │   ├── semantic.py            # Análisis semántico, scopes y tabla de símbolos
│   │   ├── ir_generator.py        # Generación de código intermedio
│   │   ├── optimizer.py           # Optimización de IR, bloques básicos, CFG y métricas U3
│   │   ├── interference_graph.py  # Grafos de interferencia
│   │   ├── native_ir.py           # IR tipado y con ámbitos para generación de código objeto
│   │   ├── register_allocator.py  # Análisis de vida hacia atrás y asignación de registros
│   │   └── object_code.py         # Backend emisor de código objeto x86-64 Linux
│   ├── templates/
│   │   └── index.html             # Interfaz web
│   └── main.py                    # Punto de entrada de la aplicación FastAPI
├── README.md                      # Este documento
└── requirements.txt               # Lista de dependencias fijadas
```
