# 🏗️ Rigger 360° — Ingeniería de Izaje

Calculadora técnica de **planes de izaje y rigging** bajo referencia normativa **ASME B30.5 / B30.9 / B30.26**. Construida con [Streamlit](https://streamlit.io/) y Python.

> 🇬🇧 English version below — [jump to English](#-english).

---

## ✨ Funcionalidades

- **Cálculo de maniobra**: peso bruto, fuerza de viento, tensión por ramal, utilización de grúa, eslingas, grilletes y presión sobre el terreno.
- **CG asimétrico** y **maniobra tándem** (2 grúas).
- **Curvas LMI** (capacidad vs radio) por equipo, con punto operativo y zonas de seguridad.
- **Generación de PDF** con memoria de cálculo paso a paso, diagramas y cuadro de firmas.
- **Historial** de planes con exportación a CSV, clonado y borrado.
- **Registro de equipos** con editor de tabla de carga.
- Semáforo de decisión **GO / CRÍTICO / NO-GO**.

## 🖥️ Requisitos

- Python 3.10 o superior.

## 🚀 Ejecución local

```bash
# 1. Clonar
git clone https://github.com/<usuario>/rigger-360.git
cd rigger-360

# 2. Entorno virtual (recomendado)
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Ejecutar
streamlit run calculadora_izaje.py
```

La app abre en `http://localhost:8501`.

## ⚙️ Configuración

| Variable de entorno | Descripción | Por defecto |
|---|---|---|
| `IZAJE_DB_PATH` | Ruta del archivo SQLite | `./izaje.db` |
| `IZAJE_DATA_DIR` | Carpeta de datos | carpeta del script |

> ⚠️ **No** ejecutes con la base de datos dentro de OneDrive/Dropbox: la sincronización de archivos puede provocar bloqueos. Usa `IZAJE_DB_PATH` para apuntar a una carpeta local o a un volumen persistente.

## ☁️ Despliegue en producción

Esta es una app **Streamlit** (servidor Python con WebSockets). Opciones recomendadas:

| Plataforma | Esfuerzo | Notas |
|---|---|---|
| **Streamlit Community Cloud** | Mínimo | Deploy directo desde GitHub. Ideal para demo/validación. |
| **Render / Railway / Fly.io** | Bajo | Contenedor desde GitHub, HTTPS, variables de entorno. Recomendado para producción. |
| **VPS + Docker** | Medio | Control total (nginx + certbot). |

Para multiusuario real, migrar de SQLite a **PostgreSQL/Supabase** y añadir autenticación.

> ❌ Cloudflare Pages y cPanel (WSGI) **no** sirven para hostear Streamlit directamente. Cloudflare sí es útil delante como CDN/dominio.

## 📐 Notas de ingeniería

- El **viento** se contabiliza una sola vez (empuje sobre la vela sumado a la carga). El umbral de NO-GO por viento es **configurable** (por defecto 32 Km/h ≈ 9 m/s).
- La **presión sobre el terreno** usa el peso operativo real de la grúa (campo editable), no una estimación fija.
- El factor de seguridad del material se asume **incluido en el WLL** ingresado.

> ⚠️ **Aviso**: herramienta de apoyo a la ingeniería. Los resultados deben ser validados por un profesional competente y contrastados con las tablas oficiales del fabricante antes de cualquier maniobra real.

## 📁 Estructura

```
.
├── calculadora_izaje.py     # Aplicación (UI + motor de cálculo + PDF)
├── requirements.txt         # Dependencias
├── .streamlit/config.toml   # Tema y configuración de servidor
├── .gitignore
└── README.md
```

---

## 🇬🇧 English

**Rigger 360°** is a technical calculator for **lifting & rigging plans** under **ASME B30.5 / B30.9 / B30.26** references, built with Streamlit and Python.

### Features
Maneuver calculation (gross load, wind force, sling tension, crane/sling/shackle utilization, ground bearing pressure), asymmetric CG, tandem lifts, LMI charts, step-by-step PDF reports, history with CSV export, and a GO / CRITICAL / NO-GO decision badge.

### Quick start
```bash
pip install -r requirements.txt
streamlit run calculadora_izaje.py
```

### Configuration
Set `IZAJE_DB_PATH` to place the SQLite database outside synced folders (OneDrive/Dropbox).

### Deployment
It is a Streamlit app (persistent Python server with WebSockets). Use **Streamlit Community Cloud**, **Render/Railway/Fly.io**, or a **Docker VPS**. Cloudflare Pages and cPanel (WSGI) cannot host Streamlit directly. For multi-user production, migrate SQLite → PostgreSQL/Supabase and add authentication.

> ⚠️ **Disclaimer**: engineering support tool. Results must be validated by a competent professional against the manufacturer's official load charts before any real lift.
