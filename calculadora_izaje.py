import base64
import json
import math
import os
import sqlite3
import io
from datetime import datetime

import pandas as pd
import streamlit as st

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURACIÓN Y BASE DE DATOS ---
# La ruta de la base de datos es configurable por variable de entorno IZAJE_DB_PATH.
# Esto permite sacar el archivo de carpetas sincronizadas (OneDrive/Dropbox), que
# provocan bloqueos de archivo, y apuntarlo a un volumen persistente en producción.
BASE_DATA_DIR = os.environ.get("IZAJE_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.environ.get("IZAJE_DB_PATH", os.path.join(BASE_DATA_DIR, "izaje.db"))
LOGO_APP = None
LOGO_CLIENTE = None

def _conectar(db_path):
    """Abre una conexión SQLite endurecida para acceso concurrente.

    WAL permite lecturas simultáneas mientras se escribe y busy_timeout evita
    los errores 'database is locked' cuando varios usuarios operan a la vez.
    """
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except sqlite3.Error:
        pass
    return conn

def obtener_logo_cliente(nombre):
    return None

def ejecutar_query(db_path, query, params=(), commit=False):
    conn = _conectar(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
        return cursor.fetchall()
    finally:
        conn.close()

def obtener_dataframe(db_path, query, params=()):
    conn = _conectar(db_path)
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

def init_db():
    conn = _conectar(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS especificaciones_equipos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identificador TEXT UNIQUE,
        peso_gancho_kg REAL,
        capacidad_max_ton REAL,
        empresa_id INTEGER
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT,
        identificador TEXT UNIQUE,
        nombre TEXT,
        empresa_id INTEGER
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tablas_carga_equipos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identificador TEXT,
        radio_m REAL,
        capacidad_kg REAL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_rigging_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        descripcion TEXT,
        responsable TEXT,
        datos_json TEXT,
        empresa_id INTEGER,
        contrato_id INTEGER
    )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM especificaciones_equipos")
    if cursor.fetchone()[0] == 0:
        specs = [
            ("Liebherr LTM 1050-3.1", 300.0, 50.0, 0),
            ("Grove GMK 3060-1", 250.0, 60.0, 0),
            ("Tadano ATF 100G-4", 450.0, 100.0, 0)
        ]
        cursor.executemany("INSERT INTO especificaciones_equipos (identificador, peso_gancho_kg, capacidad_max_ton, empresa_id) VALUES (?, ?, ?, ?)", specs)
        
        ltm_chart = [
            ("Liebherr LTM 1050-3.1", 3.0, 50000.0),
            ("Liebherr LTM 1050-3.1", 4.0, 42000.0),
            ("Liebherr LTM 1050-3.1", 5.0, 35000.0),
            ("Liebherr LTM 1050-3.1", 6.0, 29000.0),
            ("Liebherr LTM 1050-3.1", 8.0, 20500.0),
            ("Liebherr LTM 1050-3.1", 10.0, 15000.0),
            ("Liebherr LTM 1050-3.1", 12.0, 11500.0),
            ("Liebherr LTM 1050-3.1", 14.0, 9000.0),
            ("Liebherr LTM 1050-3.1", 16.0, 7200.0),
            ("Liebherr LTM 1050-3.1", 18.0, 5900.0),
            ("Liebherr LTM 1050-3.1", 20.0, 4900.0),
        ]
        gmk_chart = [
            ("Grove GMK 3060-1", 3.0, 60000.0),
            ("Grove GMK 3060-1", 4.0, 48000.0),
            ("Grove GMK 3060-1", 5.0, 39000.0),
            ("Grove GMK 3060-1", 6.0, 31000.0),
            ("Grove GMK 3060-1", 8.0, 21000.0),
            ("Grove GMK 3060-1", 10.0, 15200.0),
            ("Grove GMK 3060-1", 12.0, 11700.0),
            ("Grove GMK 3060-1", 14.0, 9200.0),
            ("Grove GMK 3060-1", 16.0, 7400.0),
            ("Grove GMK 3060-1", 18.0, 6000.0),
            ("Grove GMK 3060-1", 20.0, 5000.0),
        ]
        tadano_chart = [
            ("Tadano ATF 100G-4", 3.0, 100000.0),
            ("Tadano ATF 100G-4", 4.0, 85000.0),
            ("Tadano ATF 100G-4", 5.0, 70000.0),
            ("Tadano ATF 100G-4", 6.0, 58000.0),
            ("Tadano ATF 100G-4", 8.0, 42000.0),
            ("Tadano ATF 100G-4", 10.0, 31000.0),
            ("Tadano ATF 100G-4", 12.0, 24000.0),
            ("Tadano ATF 100G-4", 14.0, 19200.0),
            ("Tadano ATF 100G-4", 16.0, 15600.0),
            ("Tadano ATF 100G-4", 18.0, 13000.0),
            ("Tadano ATF 100G-4", 20.0, 10800.0),
        ]
        cursor.executemany("INSERT INTO tablas_carga_equipos (identificador, radio_m, capacidad_kg) VALUES (?, ?, ?)", ltm_chart + gmk_chart + tadano_chart)
        
        registros = [
            ("Elementos de izaje", "ES-SYN-5T", "Eslinga Sintética 5 Ton 4m", 0),
            ("Elementos de izaje", "ES-STE-10T", "Estrobo de Acero 10 Ton 6m", 0),
            ("Elementos de izaje", "ES-CHN-8T", "Cadena de Grado 80 8 Ton 3m", 0),
            ("Camion_Transporte", "GR-MOB-01", "Grúa Móvil Liebherr LTM 1050 [Patente AB-CD-12]", 0),
            ("Equipo_Pesado", "GR-MOB-02", "Grúa Móvil Grove 3060 [Patente WX-YZ-34]", 0),
            ("Equipo_Pesado", "GR-MOB-03", "Grúa Móvil Tadano 100G [Patente EF-GH-56]", 0)
        ]
        cursor.executemany("INSERT INTO registros (categoria, identificador, nombre, empresa_id) VALUES (?, ?, ?, ?)", registros)
        
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    import sys
    print(f"[init_db] Advertencia: no se pudo inicializar la base de datos: {e}", file=sys.stderr)

# --- VISUALIZACIONES GRÁFICAS DE IZAJE ---
def draw_rigging_diagram(d1, d2, angulo=90, asimetrico=False, tandem=False, tension_a=0, tension_b=0, util_a=0, util_b=0, dark_mode=True):
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=100)
    ax.set_aspect('equal')
    
    bg_color = '#0f172a' if dark_mode else '#ffffff'
    load_color = '#38bdf8' if dark_mode else '#475569'
    ground_color = '#334155' if dark_mode else '#cbd5e1'
    hook_color = '#f8fafc' if dark_mode else '#1e293b'
    text_color = '#cbd5e1' if dark_mode else '#0f172a'
    line_color = '#475569' if dark_mode else '#94a3b8'
    
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    def get_color_from_util(util):
        if util > 100: return '#ef4444' # Rojo
        if util > 75: return '#eab308' # Amarillo
        return '#10b981' # Verde
        
    if tandem:
        # Dibujar carga
        ax.bar([0], [1.0], width=4.0, bottom=0, color=load_color, alpha=0.8, edgecolor=hook_color, linewidth=1.5)
        
        # Tensiones/colores de eslinga
        color_a = get_color_from_util(util_a) if util_a > 0 else '#ef4444'
        color_b = get_color_from_util(util_b) if util_b > 0 else '#ef4444'
        
        # Ramal A y B (con flechas indicando fuerza)
        ax.annotate("", xy=(-1.5, 3.0), xytext=(-1.5, 1.0),
                    arrowprops=dict(arrowstyle="->", color=color_a, lw=2.5, shrinkA=0, shrinkB=5))
        ax.annotate("", xy=(1.5, 3.0), xytext=(1.5, 1.0),
                    arrowprops=dict(arrowstyle="->", color=color_b, lw=2.5, shrinkA=0, shrinkB=5, linestyle='--'))
        
        if tension_a > 0:
            ax.text(-2.4, 2.0, f"{tension_a:,.0f} Kg\n({util_a:.1f}%)", color=color_a, fontsize=8, fontweight='bold')
        if tension_b > 0:
            ax.text(1.7, 2.0, f"{tension_b:,.0f} Kg\n({util_b:.1f}%)", color=color_b, fontsize=8, fontweight='bold')
            
        # Ganchos
        ax.plot(-1.5, 3.0, marker='o', markersize=10, color=hook_color)
        ax.plot(1.5, 3.0, marker='o', markersize=10, color=hook_color)
        ax.text(-1.5, 3.2, 'Gancho A', ha='center', fontsize=9, fontweight='bold', color=hook_color)
        ax.text(1.5, 3.2, 'Gancho B', ha='center', fontsize=9, fontweight='bold', color=hook_color)
        
        # CG
        ax.plot(0, 0.5, marker='X', markersize=12, color='#eab308', markeredgecolor=hook_color)
        ax.text(0, 0.7, 'CG', ha='center', fontsize=9, fontweight='bold', color=text_color)
    else:
        load_w = 3.0
        load_h = 1.0
        ax.bar([0], [load_h], width=load_w, bottom=0, color=load_color, alpha=0.8, edgecolor=hook_color, linewidth=1.5)
        
        color_a = get_color_from_util(util_a) if util_a > 0 else '#ef4444'
        color_b = get_color_from_util(util_a) if util_a > 0 else '#ef4444' # misma eslinga en simple simétrica
        
        if asimetrico:
            total_d = d1 + d2
            p_left = -1.5
            p_right = 1.5
            x_cg = p_left + (d1 / total_d) * 3.0
            x_cg = max(-1.4, min(1.4, x_cg))
            x_hook = x_cg
            h_hook = 1.0 + (1.5 * np.tan(np.radians(angulo)))
            
            # Dibujar eslingas con flechas
            ax.annotate("", xy=(x_hook, h_hook), xytext=(p_left, load_h),
                        arrowprops=dict(arrowstyle="->", color=color_a, lw=2.5, shrinkA=0, shrinkB=5))
            ax.annotate("", xy=(x_hook, h_hook), xytext=(p_right, load_h),
                        arrowprops=dict(arrowstyle="->", color=color_b, lw=2.5, shrinkA=0, shrinkB=5))
            
            # CG y Línea de Plomada del Gancho
            ax.plot(x_cg, load_h/2, marker='X', markersize=12, color='#eab308', markeredgecolor=hook_color)
            ax.text(x_cg, load_h/2 + 0.15, 'CG Asim.', ha='center', fontsize=9, fontweight='bold', color=text_color)
            
            # Línea vertical del gancho (Plomada)
            ax.axvline(x_hook, color=line_color, linestyle=':', linewidth=1.2)
            
            if tension_a > 0:
                ax.text(-2.4, load_h + 0.5, f"T1: {tension_a:,.0f} Kg", color=color_a, fontsize=8, fontweight='bold')
                # la tensión del otro ramal se puede estimar
                tension_b_val = (tension_a * d1 / d2) if d2 > 0 else tension_a
                ax.text(1.6, load_h + 0.5, f"T2: {tension_b_val:,.0f} Kg", color=color_b, fontsize=8, fontweight='bold')
            hook_x = x_hook
        else:
            h_hook = 1.0 + (1.5 * np.tan(np.radians(angulo)))
            ax.annotate("", xy=(0, h_hook), xytext=(-1.5, load_h),
                        arrowprops=dict(arrowstyle="->", color=color_a, lw=2.5, shrinkA=0, shrinkB=5))
            ax.annotate("", xy=(0, h_hook), xytext=(1.5, load_h),
                        arrowprops=dict(arrowstyle="->", color=color_b, lw=2.5, shrinkA=0, shrinkB=5))
            
            ax.plot(0, load_h/2, marker='X', markersize=12, color='#eab308', markeredgecolor=hook_color)
            ax.text(0, load_h/2 + 0.15, 'CG', ha='center', fontsize=9, fontweight='bold', color=text_color)
            
            # Línea vertical del gancho
            ax.axvline(0, color=line_color, linestyle=':', linewidth=1.2)
            
            # Textos de ángulo
            ax.text(-1.1, load_h + 0.2, f'{angulo}°', fontsize=9, fontweight='bold', color=text_color)
            ax.text(0.8, load_h + 0.2, f'{angulo}°', fontsize=9, fontweight='bold', color=text_color)
            
            if tension_a > 0:
                ax.text(-2.4, load_h + 0.5, f"T: {tension_a:,.0f} Kg\n({util_a:.1f}%)", color=color_a, fontsize=8, fontweight='bold')
            hook_x = 0
            
        ax.plot(hook_x, h_hook, marker='o', markersize=10, color=hook_color)
        ax.text(hook_x, h_hook + 0.2, 'Gancho Principal', ha='center', fontsize=9, fontweight='bold', color=hook_color)
        
    ax.axhline(0, color=ground_color, linewidth=2, zorder=-1)
    ax.set_xlim(-4, 4)
    ax.set_ylim(-0.5, 4.5)
    ax.axis('off')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=bg_color)
    plt.close(fig)
    buf.seek(0)
    return buf

def draw_lmi_chart(radios, capacidades, radio_actual, peso_bruto, dark_mode=True):
    if not radios or not capacidades:
        return None
    
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=100)
    bg_color = '#0f172a' if dark_mode else '#ffffff'
    text_color = '#cbd5e1' if dark_mode else '#1e293b'
    grid_color = '#334155' if dark_mode else '#cbd5e1'
    line_color = '#38bdf8' if dark_mode else '#2563eb'
    
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    # 1. Dibujar curva LMI principal
    ax.plot(radios, capacidades, color=line_color, linewidth=2.5, label='Curva LMI (100%)', zorder=4)
    
    # 2. Sombreado de seguridad por zonas bajo la curva
    # Safe zone (0% to 75% capacity)
    y_safe = [c * 0.75 for c in capacidades]
    safe_color = 'rgba(16, 185, 129, 0.15)' if dark_mode else '#dcfce7'
    ax.fill_between(radios, 0, y_safe, color=safe_color, alpha=0.4 if not dark_mode else 1.0, label='Zona Segura (<75% LMI)')
    
    # Warning zone (75% to 100% capacity)
    warning_color = 'rgba(234, 179, 8, 0.2)' if dark_mode else '#fef3c7'
    ax.fill_between(radios, y_safe, capacidades, color=warning_color, alpha=0.5 if not dark_mode else 1.0, label='Zona Crítica (75%-100% LMI)')
    
    # Danger zone (Above LMI curve)
    max_y = max(capacidades) * 1.2
    danger_color = 'rgba(239, 68, 68, 0.2)' if dark_mode else '#fee2e2'
    ax.fill_between(radios, capacidades, max_y, color=danger_color, alpha=0.3 if not dark_mode else 1.0, label='Sobrecapacidad (>100% LMI)')
    
    # 3. Dibujar punto operativo actual
    if radio_actual < min(radios) or radio_actual > max(radios):
        pt_color = '#ef4444'
        label_pt = f'Punto Operativo (Fuera de Rango: {radio_actual}m)'
    else:
        cap_actual = np.interp(radio_actual, radios, capacidades)
        util_pct = (peso_bruto / cap_actual) * 100
        pt_color = '#ef4444' if util_pct > 100 else ('#eab308' if util_pct > 75 else '#10b981')
        label_pt = f'Punto de Izaje ({radio_actual}m, {peso_bruto:.0f}kg - {util_pct:.1f}%)'
        
    ax.scatter([radio_actual], [peso_bruto], color=pt_color, s=140, zorder=5, edgecolor='#0f172a', linewidth=1.5, label=label_pt)
    
    # Marcador en cruz sobre el punto
    line_style_color = '#94a3b8' if dark_mode else '#475569'
    ax.plot([radio_actual, radio_actual], [0, peso_bruto], color=line_style_color, linestyle=':', linewidth=1)
    ax.plot([min(radios), radio_actual], [peso_bruto, peso_bruto], color=line_style_color, linestyle=':', linewidth=1)
    
    ax.set_xlabel('Radio de Operación (m)', fontsize=9, fontweight='bold', color=text_color)
    ax.set_ylabel('Capacidad / Carga (Kg)', fontsize=9, fontweight='bold', color=text_color)
    ax.set_title('Gráfica de Capacidad vs Radio (LMI)', fontsize=10, fontweight='bold', color=text_color)
    
    ax.set_ylim(0, max_y)
    ax.set_xlim(min(radios), max(radios))
    ax.grid(True, linestyle='--', alpha=0.4, color=grid_color)
    
    # Leyenda
    leg = ax.legend(fontsize=8, loc='upper right')
    if dark_mode:
        leg.get_frame().set_facecolor('#1e293b')
        leg.get_frame().set_edgecolor('#334155')
        for text in leg.get_texts():
            text.set_color('#cbd5e1')
            
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(grid_color)
    ax.spines['bottom'].set_color(grid_color)
    
    ax.tick_params(colors=text_color, which='both')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=bg_color)
    plt.close(fig)
    buf.seek(0)
    return buf

class StandalonePDFEngine:
    @staticmethod
    def generar(template_name, obj, logo_app=None, logo_cliente=None):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=18,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#475569'),
            spaceAfter=8
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#0f172a'),
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#334155')
        )
        body_bold_style = ParagraphStyle(
            'BodyBoldStyle',
            parent=body_style,
            fontName='Helvetica-Bold'
        )
        math_style = ParagraphStyle(
            'MathStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0f172a'),
            leftIndent=15,
            spaceAfter=3
        )
        
        story.append(Paragraph("PLAN DE IZAJE Y RIGGING", title_style))
        story.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Rigger 360°", subtitle_style))
        
        # --- Page 1: General Info & Crane Details ---
        info_data = [
            [Paragraph("<b>Descripción Trabajo:</b>", body_style), Paragraph(obj.get('descripcion', 'Izaje Estándar'), body_style),
             Paragraph("<b>Área de Vela:</b>", body_style), Paragraph(f"{obj.get('area_vela_m2', 5.0)} m² ({obj.get('tipo_carga', 'Normal')})", body_style)],
            [Paragraph("<b>Empresa Solicitante:</b>", body_style), Paragraph(obj.get('empresa', 'CGT'), body_style),
             Paragraph("<b>Límite Suelo:</b>", body_style), Paragraph(f"{obj.get('limite_suelo', 20000.0)/1000.0:.1f} Ton/m²", body_style)],
            [Paragraph("<b>Peso Neto Carga:</b>", body_style), Paragraph(f"{obj.get('p_neto_total', 0):,.1f} Kg", body_style),
             Paragraph("<b>Dim. Pads:</b>", body_style), Paragraph(f"{obj.get('pad_ancho', 1.0)}m x {obj.get('pad_largo', 1.0)}m", body_style)],
            [Paragraph("<b>Velocidad Viento:</b>", body_style), Paragraph(f"{obj.get('viento', 0)} Km/h", body_style),
             Paragraph("<b>Esquema de Izaje:</b>", body_style), Paragraph("Tándem (2 Grúas)" if obj.get('es_tandem') else "Simple", body_style)]
        ]
        info_table = Table(info_data, colWidths=[110, 160, 110, 160])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 4))
        
        def add_crane_details(key_name, label):
            g_data = obj.get(key_name)
            if not g_data:
                return
            story.append(Paragraph(f"<b>Especificaciones del Equipo: {label}</b> ({g_data.get('id')})", heading_style))
            details_data = [
                [Paragraph("<b>Radio / Ángulo Pluma:</b>", body_style), Paragraph(f"{g_data.get('radio')} m @ {g_data.get('angulo')}°", body_style),
                 Paragraph("<b>Capacidad de Tabla:</b>", body_style), Paragraph(f"{g_data.get('capacidad', 0):,.1f} Kg", body_style)],
                [Paragraph("<b>Peso Bruto (con Viento):</b>", body_style), Paragraph(f"{g_data.get('bruta_con_viento', 0):,.1f} Kg (Viento: {g_data.get('drag_force_kg', 0):,.1f} Kg)", body_style),
                 Paragraph("<b>Porcentaje Utilización:</b>", body_style), Paragraph(f"<b>{g_data.get('utilizacion', 0):,.1f}%</b>", body_bold_style)],
                [Paragraph("<b>Aparejo / Modo:</b>", body_style), Paragraph(f"{g_data.get('material', '')} ({g_data.get('tipo_amarre', '')})", body_style),
                 Paragraph("<b>Estrés del Aparejo:</b>", body_style), Paragraph(f"<b>{g_data.get('util_rigging', 0):,.1f}%</b> (WLL Efec: {g_data.get('wll_efectivo', 0):,.0f} Kg)", body_bold_style)],
                [Paragraph("<b>Tensión en Ramal:</b>", body_style), Paragraph(f"{g_data.get('tension', 0):,.1f} Kg (WLL Grillete: {g_data.get('shackle_wll', 0):,.0f} Kg)", body_style),
                 Paragraph("<b>Estrés Grillete / Suelo:</b>", body_style), Paragraph(f"<b>G: {g_data.get('shackle_util', 0):,.1f}% / S: {g_data.get('suelo_util', 0):,.1f}%</b>", body_bold_style)]
            ]
            t_details = Table(details_data, colWidths=[130, 140, 130, 140])
            t_details.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('BACKGROUND', (3,1), (3,1), colors.HexColor('#fef2f2') if g_data.get('utilizacion',0) > 75 else colors.HexColor('#f0fdf4')),
                ('BACKGROUND', (3,2), (3,2), colors.HexColor('#fef2f2') if g_data.get('util_rigging',0) > 75 else colors.HexColor('#f0fdf4')),
            ]))
            story.append(t_details)
            story.append(Spacer(1, 4))

        add_crane_details('grua_a', "Unidad A")
        add_crane_details('grua_b', "Unidad B (Tándem)")
        
        # --- Generar Gráficos en Calidad Limpia / Fondo Claro para PDF ---
        d1 = obj.get('d1', 2.0)
        d2 = obj.get('d2', 1.0)
        cg_asim = obj.get('cg_asim', False)
        es_tandem = obj.get('es_tandem', False)
        res_a = obj.get('grua_a', {})
        res_b = obj.get('grua_b', {})
        
        img_diag_buf = draw_rigging_diagram(
            d1, d2,
            angulo=res_a.get('angulo', 90),
            asimetrico=cg_asim,
            tandem=es_tandem,
            tension_a=res_a.get('tension', 0),
            tension_b=res_b.get('tension', 0) if es_tandem else 0,
            util_a=res_a.get('util_rigging', 0),
            util_b=res_b.get('util_rigging', 0) if es_tandem else 0,
            dark_mode=False
        )
        
        img_lmi_buf = None
        if res_a.get('lmi_radios'):
            img_lmi_buf = draw_lmi_chart(
                res_a['lmi_radios'],
                res_a['lmi_caps'],
                res_a['radio'],
                res_a['bruta_con_viento'],
                dark_mode=False
            )
            
        img_diag = Image(img_diag_buf, width=250, height=165)
        if img_lmi_buf:
            img_lmi = Image(img_lmi_buf, width=250, height=165)
            charts_table = Table([[img_diag, img_lmi]], colWidths=[270, 270])
        else:
            charts_table = Table([[img_diag]], colWidths=[540])
            
        charts_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        
        story.append(Spacer(1, 4))
        story.append(charts_table)
        story.append(Spacer(1, 4))
        
        max_util = max(obj.get('grua_a', {}).get('utilizacion', 0), obj.get('grua_b', {}).get('utilizacion', 0) if obj.get('es_tandem') else 0)
        max_rig = max(obj.get('grua_a', {}).get('util_rigging', 0), obj.get('grua_b', {}).get('util_rigging', 0) if obj.get('es_tandem') else 0)
        max_sh = max(obj.get('grua_a', {}).get('shackle_util', 0), obj.get('grua_b', {}).get('shackle_util', 0) if obj.get('es_tandem') else 0)
        max_suelo = max(obj.get('grua_a', {}).get('suelo_util', 0), obj.get('grua_b', {}).get('suelo_util', 0) if obj.get('es_tandem') else 0)
        viento = obj.get('viento', 0)
        viento_max = obj.get('viento_max', 32)

        if max_util > 100 or max_rig > 100 or max_sh > 100 or max_suelo > 100 or viento >= viento_max:
            status_text = "ESTADO: NO AUTORIZADO (NO-GO) ❌"
            bg_badge = colors.HexColor('#fee2e2')
            text_color = colors.HexColor('#991b1b')
        elif max_util > 75 or max_rig > 75 or max_sh > 75 or max_suelo > 75:
            status_text = "ESTADO: IZAJE CRÍTICO (REFIERA A SUPERVISIÓN) ⚠️"
            bg_badge = colors.HexColor('#fef3c7')
            text_color = colors.HexColor('#92400e')
        else:
            status_text = "ESTADO: OPERACIÓN SEGURA ✅"
            bg_badge = colors.HexColor('#dcfce7')
            text_color = colors.HexColor('#166534')
            
        status_style = ParagraphStyle(
            'StatusStyle',
            parent=body_bold_style,
            fontSize=10,
            leading=12,
            textColor=text_color,
            alignment=1
        )
        
        status_table = Table([[Paragraph(status_text, status_style)]], colWidths=[540])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_badge),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 1.2, text_color),
        ]))
        story.append(status_table)
        
        # --- Page 2: Mathematical Memory and Signatures ---
        story.append(PageBreak())
        story.append(Paragraph("<b>MEMORIA DE CÁLCULO TÉCNICO Y ECUACIONES (PASO A PASO)</b>", heading_style))
        story.append(Spacer(1, 6))
        
        def append_math_details(key_name, label):
            g = obj.get(key_name)
            if not g:
                return
            story.append(Paragraph(f"<b>Grúa / Equipo: {label} ({g['id']})</b>", body_bold_style))
            story.append(Spacer(1, 2))
            
            # 1. Fuerza de arrastre
            f_wind_text = f"<b>1. Fuerza de arrastre por viento (Fw) - ASME B30.5:</b><br/>" \
                          f"Fórmula: <i>Fw = 0.00482 * V² * A_vela * Cd</i><br/>" \
                          f"Valores: 0.00482 * {obj['viento']}² * {obj['area_vela_m2']} * {1.5 if obj['tipo_carga']=='Media' else (2.0 if obj['tipo_carga']=='Alta' else 1.2)} = <b>{g['drag_force_kg']:.1f} Kg</b>"
            story.append(Paragraph(f_wind_text, math_style))
            
            # 2. Carga bruta
            f_gross_text = f"<b>2. Carga bruta total en gancho (Pbruta):</b><br/>" \
                           f"Fórmula: <i>Pbruta = Pneto_prop + Rigging + Fw</i><br/>" \
                           f"Valores: ({obj['p_neto_total']:.0f} * {g['dist_p']/100:.2f}) + {g['rigging']:.0f} + {g['drag_force_kg']:.1f} = <b>{g['bruta_con_viento']:.1f} Kg</b>"
            story.append(Paragraph(f_gross_text, math_style))
            
            # 3. Tensión y factor de ángulo
            if obj.get('cg_asim') and not obj.get('es_tandem'):
                f_tension_text = f"<b>3. Tensión del Aparejo (CG Asimétrico):</b><br/>" \
                                 f"Fórmula: <i>T = Pbruta * (d_opuesta / (d1+d2)) * fa</i> con <i>fa = 1 / sin(θ)</i><br/>" \
                                 f"Valores: fa = 1 / sin({g['angulo']}°) = {g['factor_angulo']:.3f}. T = {g['tension']:.1f} Kg"
            else:
                f_tension_text = f"<b>3. Tensión del Aparejo (Símétrica/Tándem):</b><br/>" \
                                 f"Fórmula: <i>T = (Pbruta * fa) / N_ramales</i> con <i>fa = 1 / sin(θ)</i><br/>" \
                                 f"Valores: fa = 1 / sin({g['angulo']}°) = {g['factor_angulo']:.3f}. T = ({g['bruta_con_viento']:.1f} * {g['factor_angulo']:.3f}) / {g['ramales']} = <b>{g['tension']:.1f} Kg</b>"
            story.append(Paragraph(f_tension_text, math_style))
            
            # 4. Presión en el terreno
            peso_propio_grua = g.get('peso_propio_grua', g.get('capacidad_max_ton', 50.0) * 1000)
            f_soil_text = f"<b>4. Reacción del estabilizador y Presión en Suelo (Psuelo):</b><br/>" \
                          f"Fórmula: <i>F_outrigger = 0.75 * (W_grua + Pbruta * F_tandem)</i>,  <i>Psuelo = F_outrigger / Area_Pad</i><br/>" \
                          f"Valores: F_outrigger = 0.75 * ({peso_propio_grua:,.0f} Kg + {g['bruta']:.0f} Kg * {g['factor_tandem']}) = {g['f_outrigger_kg']:,.0f} Kg<br/>" \
                          f"Presión: {g['f_outrigger_kg']:,.0f} / ({obj['pad_ancho']} * {obj['pad_largo']}) = <b>{g['presion_suelo_ton_m2']:.1f} Ton/m²</b> (Límite: {obj['limite_suelo']/1000:.1f} Ton/m²)"
            story.append(Paragraph(f_soil_text, math_style))
            story.append(Spacer(1, 4))
            
        append_math_details('grua_a', "Unidad A")
        append_math_details('grua_b', "Unidad B (Tándem)")
        
        # --- Cuadro de Firmas ---
        story.append(Spacer(1, 15))
        firma_data = [
            ["", "", ""],
            ["___________________________", "___________________________", "___________________________"],
            ["Operador de Grúa", "Rigger de Maniobra", "Supervisor de Izaje"],
            ["Firma / Rut:", "Firma / Rut:", "Firma / Rut:"]
        ]
        firma_table = Table(firma_data, colWidths=[180, 180, 180])
        firma_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#475569')),
            ('FONTNAME', (0,2), (-1,2), 'Helvetica-Bold'),
            ('FONTSIZE', (0,2), (-1,3), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(firma_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

pdf_engine = StandalonePDFEngine()

# --- CONSTANTES DE INGENIERÍA RIGGER 360 ---
FACTORES_ANGULO = {90: 1.0, 60: 1.2, 50: 1.305, 45: 1.414, 30: 2.0}
FACTORES_MODO = {"Axial (1.0)": 1.0, "Lazo (0.8)": 0.8, "Cesto/U (2.0)": 2.0}
FACTORES_MATERIAL = {"Eslinga Sintética (SF 7:1)": 7.0, "Estrobo Acero (SF 5:1)": 5.0, "Cadena Aleación (SF 4:1)": 4.0}
FACTORES_VELA = {"Normal": 1.0, "Media (Cajas)": 1.5, "Alta (Paneles)": 2.5}
FV = {"Normal": 1.0, "Media": 1.5, "Alta": 2.5}

TABLA_GRILLETES = {
    '1/2" (WLL 2.0t)': 2000.0,
    '5/8" (WLL 3.25t)': 3250.0,
    '3/4" (WLL 4.75t)': 4750.0,
    '7/8" (WLL 6.5t)': 6500.0,
    '1" (WLL 8.5t)': 8500.0,
    '1-1/4" (WLL 12.0t)': 12000.0,
    '1-1/2" (WLL 17.0t)': 17000.0
}
TABLA_DD = {
    'D/d >= 20 (Eficiencia 100%)': 1.00,
    'D/d = 10 (Eficiencia 92%)': 0.92,
    'D/d = 5 (Eficiencia 85%)': 0.85,
    'D/d = 2 (Eficiencia 65%)': 0.65,
    'No aplica / Otro material': 1.00
}
TABLA_SUELOS = {
    'Arcilla blanda (Límite 10 t/m²)': 10000.0,
    'Arena suelta (Límite 20 t/m²)': 20000.0,
    'Grava compacta (Límite 40 t/m²)': 40000.0,
    'Roca sana (Límite 100 t/m²)': 100000.0
}

class MotorIngenieriaIzaje:
    """Clase para desacoplar la lógica matemática de la UI."""
    @staticmethod
    def calcular_maniobra(config_global, cfg_equipo):
        if not cfg_equipo: return None

        viento = config_global.get('viento', 0)
        vela = config_global.get('vela', "Normal")
        p_neto_total = config_global.get('p_neto', 0)
        es_tandem = config_global.get('es_tandem', False)

        f_tandem = 1.25 if es_tandem else 1.0
        neta_prop = p_neto_total * (cfg_equipo['dist_p'] / 100)
        bruta = neta_prop + cfg_equipo['rigging']

        # 1. Fuerza de Viento Dinámica (modelo físico ASME B30.5)
        #    Cd (coeficiente de arrastre) según la forma/exposición de la carga.
        cd_coeff = 1.2
        if vela == "Media": cd_coeff = 1.5
        elif vela == "Alta": cd_coeff = 2.0

        area_m2 = config_global.get('area_vela_m2', 5.0)
        # v (m/s) = viento (Km/h) / 3.6
        # Presión dinámica q (Pa) = 0.613 * v^2
        # Fuerza Fw (Kg) = (q * area_m2 * cd_coeff) / 9.81
        # Simplificado: Fw = 0.00482 * viento^2 * area_m2 * cd_coeff
        drag_force_kg = 0.00482 * (viento ** 2) * area_m2 * cd_coeff if viento > 0 else 0.0

        # El empuje del viento sobre la vela se suma a la carga dinámica en el gancho.
        # NOTA DE INGENIERÍA: el viento se contabiliza UNA sola vez (lado de la carga).
        # Se eliminó la antigua reducción lineal de capacidad ("red_viento") porque,
        # sumada al arrastre, contabilizaba el viento dos veces e inflaba la utilización.
        # Por encima del límite operativo se exige consultar la tabla reducida del fabricante.
        bruta_con_viento = bruta + drag_force_kg

        cap_efectiva = cfg_equipo['capacidad']
        red_viento = 0.0
        utilizacion = (bruta_con_viento * f_tandem / cap_efectiva * 100) if cap_efectiva > 0 else 999

        # 2. Factor de Ángulo Trigonométrico
        angulo = cfg_equipo.get('angulo', 90)
        angulo_rad = math.radians(angulo)
        fa = 1.0 / math.sin(angulo_rad) if math.sin(angulo_rad) > 0 else 1.0

        # 3. Factor D/d para estrobos de acero
        dd_factor = cfg_equipo.get('dd_factor', 1.0)
        wll_efectivo = cfg_equipo['wll_base'] * dd_factor

        fm = FACTORES_MODO.get(cfg_equipo['tipo_amarre'], 1.0)
        sf = FACTORES_MATERIAL.get(cfg_equipo.get('material', "Eslinga Sintética (SF 7:1)"), 7.0)
        ram_seguros = min(cfg_equipo['ramales'], 3)
        
        # El WLL del sistema de eslingas se reduce con el factor D/d
        cap_sistema = (wll_efectivo * fm) * ram_seguros
        ruptura_estimada = wll_efectivo * sf

        if config_global.get('cg_asim') and not es_tandem:
            d1, d2 = config_global.get('d1', 1.0), config_global.get('d2', 1.0)
            t_max_base = max(bruta * (d2 / (d1 + d2)), bruta * (d1 / (d1 + d2)))
            tension_ramal = t_max_base * fa
        else:
            tension_ramal = (bruta * fa) / ram_seguros

        util_rigging = (tension_ramal * ram_seguros / cap_sistema * 100) if cap_sistema > 0 else 999

        # 4. Utilización de Grillete
        shackle_wll = cfg_equipo.get('shackle_wll', 4750.0)
        shackle_util = (tension_ramal / shackle_wll * 100) if shackle_wll > 0 else 0.0

        # 5. Presión sobre el Terreno (Outriggers)
        # Peso operativo real de la grúa (chasis + contrapeso). Si el usuario lo
        # ingresa, se usa ese valor; si no, se estima con un factor más realista
        # para grúas todoterreno (~1.0 t de grúa por t de capacidad) en lugar del
        # antiguo 1.2 que sobreestimaba el peso.
        cap_max_ton = cfg_equipo.get('capacidad_max_ton', 50.0)
        peso_grua_kg = cfg_equipo.get('peso_operativo_kg', 0) or 0
        if peso_grua_kg <= 0:
            peso_grua_kg = cap_max_ton * 1000.0
        peso_propio_grua = peso_grua_kg

        # Reacción máxima en un estabilizador durante el giro (un cuadrante toma
        # hasta el 75% del peso total: condición de borde conservadora y realista).
        f_outrigger_kg = 0.75 * (peso_propio_grua + (bruta * f_tandem))
        
        pad_ancho = config_global.get('pad_ancho', 1.0)
        pad_largo = config_global.get('pad_largo', 1.0)
        pad_area = pad_ancho * pad_largo
        presion_suelo = f_outrigger_kg / pad_area if pad_area > 0 else 0
        presion_suelo_ton_m2 = presion_suelo / 1000.0
        
        limite_suelo = config_global.get('limite_suelo', 20000.0)
        suelo_util = (presion_suelo / limite_suelo * 100) if limite_suelo > 0 else 0.0

        return {
            **cfg_equipo, 
            "bruta": bruta, 
            "cap_efectiva": cap_efectiva,
            "utilizacion": utilizacion, 
            "util_rigging": util_rigging, 
            "tension": tension_ramal,
            "cap_real_wll": cap_sistema / ram_seguros, 
            "red_viento": red_viento,
            "factor_angulo": fa, 
            "factor_tandem": f_tandem, 
            "ruptura_estimada": ruptura_estimada,
            "drag_force_kg": drag_force_kg,
            "bruta_con_viento": bruta_con_viento,
            "shackle_util": shackle_util,
            "presion_suelo_ton_m2": presion_suelo_ton_m2,
            "suelo_util": suelo_util,
            "f_outrigger_kg": f_outrigger_kg,
            "wll_efectivo": wll_efectivo,
            "peso_propio_grua": peso_propio_grua
        }

def render_calculadora_izaje(db_path, filtros):
    # Inyectar estilos CSS premium para la versión autónoma
    st.markdown("""
        <style>
        /* Color de fondo global de la app y textos */
        .stApp {
            background-color: #0b0f19 !important;
            color: #f8fafc !important;
        }
        
        /* Premium Header en Modo Oscuro */
        .premium-header {
            background: linear-gradient(135deg, #1e293b, #0f172a) !important;
            padding: 15px 20px !important;
            border-radius: 12px !important;
            border: 1px solid #334155 !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
            margin-bottom: 16px !important;
        }
        
        /* Tarjeta métrica premium en Modo Oscuro */
        .metric-card-cgt {
            background: #1e293b !important;
            border-radius: 12px !important;
            padding: 16px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
            border: 1px solid #334155 !important;
            margin-bottom: 12px !important;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out !important;
        }
        .metric-card-cgt:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15) !important;
        }
        .metric-label-cgt {
            font-size: 0.8rem !important;
            color: #94a3b8 !important;
            font-weight: 600 !important;
            margin-bottom: 6px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }
        .metric-value-cgt {
            font-size: 1.85rem !important;
            font-weight: 800 !important;
            line-height: 1 !important;
            margin: 0 !important;
        }
        
        /* Status Badge en la Calculadora */
        .status-badge {
            padding: 10px 20px !important;
            border-radius: 9999px !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            text-align: center !important;
            margin: 15px 0 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }
        .status-safe {
            background-color: rgba(16, 185, 129, 0.15) !important;
            color: #10b981 !important;
            border: 1px solid rgba(16, 185, 129, 0.3) !important;
        }
        .status-warning {
            background-color: rgba(234, 179, 8, 0.15) !important;
            color: #eab308 !important;
            border: 1px solid rgba(234, 179, 8, 0.3) !important;
        }
        .status-danger {
            background-color: rgba(239, 68, 68, 0.15) !important;
            color: #ef4444 !important;
            border: 1px solid rgba(239, 68, 68, 0.3) !important;
        }
        
        /* Estilos del Expander de Streamlit */
        .streamlit-expanderHeader {
            background-color: #1e293b !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
        }
        .streamlit-expanderContent {
            background-color: #111827 !important;
            border: 1px solid #334155 !important;
            border-top: none !important;
            border-radius: 0 0 8px 8px !important;
            padding: 12px !important;
        }
        
        /* Ajuste de espaciados compactos en Streamlit */
        div[data-testid=\"stVerticalBlock\"] > div {
            padding-top: 3px !important;
            padding-bottom: 3px !important;
        }
        div.block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
            max-width: 1280px !important;
        }

        /* Header flexible: en pantallas chicas el icono y el texto se reacomodan */
        .premium-header > div { flex-wrap: wrap !important; }

        /* Tipografía fluida del valor de las tarjetas: se adapta al ancho */
        .metric-value-cgt { font-size: clamp(1.4rem, 5vw, 1.85rem) !important; }

        /* ====== TABLET (<= 1024px) ====== */
        @media (max-width: 1024px) {
            div.block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; }
            .ph-title { font-size: 1.5rem !important; }
            .metric-card-cgt { padding: 14px !important; }
        }

        /* ====== MÓVIL (<= 640px) ====== */
        @media (max-width: 640px) {
            /* Streamlit ya apila columnas; reducimos huecos y márgenes para móvil */
            div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
            div[data-testid="column"] { min-width: 100% !important; }

            .premium-header { padding: 12px 14px !important; }
            .ph-title { font-size: 1.25rem !important; line-height: 1.2 !important; }
            .ph-sub { font-size: 0.78rem !important; }

            .metric-card-cgt { padding: 12px !important; margin-bottom: 8px !important; }
            .metric-label-cgt { font-size: 0.72rem !important; }
            .metric-value-cgt { font-size: 1.55rem !important; }

            .status-badge { font-size: 0.85rem !important; padding: 9px 14px !important; }

            /* Botones a ancho completo y con buen objetivo táctil */
            .stButton button, .stDownloadButton button {
                width: 100% !important;
                min-height: 44px !important;
                font-size: 0.9rem !important;
            }

            /* Imágenes de diagramas sin desbordar */
            div[data-testid="stImage"] img { width: 100% !important; height: auto !important; }
        }

        /* Objetivos táctiles cómodos en cualquier dispositivo táctil */
        @media (hover: none) {
            .stButton button, .stDownloadButton button { min-height: 44px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER PREMIUM - RIGGER 360 ---
    st.markdown("""
        <div class='premium-header'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='background: linear-gradient(135deg, #3b82f6, #2563eb); padding: 12px; border-radius: 12px; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);'>
                    <span style='font-size: 24px;'>🏗️</span>
                </div>
                <div>
                    <h1 class='ph-title' style='margin: 0; color: #f8fafc; font-size: 1.8rem; font-weight: 800; letter-spacing: -0.01em;'>Rigger 360° <span style='color:#60a5fa;'>|</span> Ingeniería de Izaje</h1>
                    <p class='ph-sub' style='margin: 2px 0 0 0; color: #94a3b8; font-size: 0.9rem;'>Cálculos Técnicos Bajo Norma ASME B30.9 / B30.5</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    is_master = st.session_state.role == "Global Admin"
    df_specs = obtener_dataframe(db_path, "SELECT * FROM especificaciones_equipos WHERE (empresa_id = ? OR empresa_id = 0 OR empresa_id IS NULL)", (st.session_state.empresa_id,))
    lista_ids = ["Manual"] + (df_specs['identificador'].tolist() if not df_specs.empty else [])
    
    # Obtener inventario de Elementos de Izaje del cliente
    df_eslingas = obtener_dataframe(db_path, "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria='Elementos de izaje' AND (empresa_id=? OR empresa_id=0 OR empresa_id IS NULL)", (st.session_state.empresa_id,))
    lista_eslingas = ["Ingreso Manual"] + (df_eslingas['identificador'] + " - " + df_eslingas['nombre']).tolist() if not df_eslingas.empty else ["Ingreso Manual"]

    # Obtener inventario de Vehículos (Camiones / Equipos Pesados)
    df_gruas = obtener_dataframe(db_path, "SELECT DISTINCT identificador, nombre FROM registros WHERE categoria IN ('Camion_Transporte', 'Equipo_Pesado') AND (empresa_id=? OR empresa_id=0 OR empresa_id IS NULL)", (st.session_state.empresa_id,))
    lista_gruas_fisicas = ["Vehículo No Enrolado"] + (df_gruas['identificador'] + " - " + df_gruas['nombre']).tolist() if not df_gruas.empty else ["Vehículo No Enrolado"]

    if 'clone_data' not in st.session_state: st.session_state.clone_data = {}
    cd = st.session_state.clone_data

    tab_calc, tab_hist, tab_equipos = st.tabs(["⚡ NUEVA MANIOBRA", "📋 SISTEMA DE REGISTROS", "🛠️ REGISTRO DE EQUIPOS"])

    with tab_calc:
        with st.expander("📦 DATOS DE LA CARGA", expanded=True):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Trabajo / Descripción", cd.get("descripcion", "Izaje Estándar"))
            client = c2.text_input("Empresa Solicitante", cd.get("empresa", st.session_state.filtros.get('empresa_nom', "CGT")))

            p_neto = st.number_input("Peso Neto de la Carga (Kg)", 1.0, 500000.0, float(cd.get("p_neto_total", 1000.0)), step=100.0)
            
            st.markdown("**🌬️ Parámetros de Viento (ASME B30.5)**")
            cw1, cw2, cw3, cw4 = st.columns(4)
            viento = cw1.slider("Velocidad del Viento (Km/h)", 0, 60, int(cd.get("viento", 15)))
            vela = cw2.selectbox("Exposición / Forma Vela", list(FV.keys()), index=list(FV.keys()).index(cd.get("tipo_carga", "Normal")) if cd.get("tipo_carga") in FV else 0)
            area_vela_m2 = cw3.number_input("Área de Vela Expuesta (m²)", 0.1, 200.0, float(cd.get("area_vela_m2", 5.0)), step=1.0)
            viento_max = cw4.number_input("Viento máx. operación (Km/h)", 10, 60, int(cd.get("viento_max", 32)), step=1,
                                          help="Límite del fabricante para suspender la maniobra. Por defecto 32 Km/h (≈9 m/s, referencia ASME B30.5). Ajústalo según la tabla de carga reducida de tu grúa.")

            c_opts1, c_opts2 = st.columns(2)
            cg_asim = c_opts1.checkbox("CG Asimétrico", value=cd.get("cg_asim", False))
            es_tandem = c_opts2.checkbox("Maniobra Tándem (2 Grúas)", value=cd.get("es_tandem", False))

            d1, d2 = 1.0, 1.0
            if cg_asim:
                ca1, ca2 = st.columns(2)
                d1 = ca1.number_input("Distancia D1 (m)", 0.1, 100.0, float(cd.get("d1", 2.0)), step=1.0)
                d2 = ca2.number_input("Distancia D2 (m)", 0.1, 100.0, float(cd.get("d2", 1.0)), step=1.0)

            dist_a = st.number_input("% Carga Grúa A", 10.0, 90.0, float(cd.get("grua_a",{}).get("dist_p", 50.0)) if es_tandem else 50.0) if es_tandem else 100.0

        with st.expander("🌱 SUELO Y ESTABILIZADORES (PRESIÓN EN TERRENO)", expanded=False):
            cs1, cs2, cs3 = st.columns(3)
            tipo_suelo = cs1.selectbox("Tipo de Suelo / Límite de Apoyo", list(TABLA_SUELOS.keys()), index=1)
            limite_suelo = TABLA_SUELOS[tipo_suelo]
            pad_ancho = cs2.number_input("Ancho del Pad de Estabilizador (m)", 0.1, 5.0, float(cd.get("pad_ancho", 1.0)), step=1.0)
            pad_largo = cs3.number_input("Largo del Pad de Estabilizador (m)", 0.1, 5.0, float(cd.get("pad_largo", 1.0)), step=1.0)

        def gui_setup_equipo(label, key, pct):
            st.markdown(f"#### {label} ({pct}%)")
            ed = cd.get(f"grua_{key}", {})

            with st.container(border=True):
                st.markdown("**✅ Checklist Pre-Uso (ASME)**")
                ck1 = st.checkbox(f"Accesorios certificados y sin daños ({key})", key=f"ck1_{key}")
                ck2 = st.checkbox(f"Gancho con seguro y operativo ({key})", key=f"ck2_{key}")

                c_top1, c_top2 = st.columns([2, 3])
                curr_id = ed.get("id", "Manual")
                idx_sel = lista_ids.index(curr_id) if curr_id in lista_ids else 0
                
                curr_fisica = ed.get("id_fisico", "Vehículo No Enrolado")
                idx_fisica = lista_gruas_fisicas.index(curr_fisica) if curr_fisica in lista_gruas_fisicas else 0
                
                st.markdown("**Identificación del Equipo**")
                c_maq1, c_maq2 = st.columns(2)
                id_eq = c_maq1.selectbox("Modelo / Tabla LMI", lista_ids, key=f"id_{key}", index=idx_sel)
                id_fisico = c_maq2.selectbox("Máquina Física (Patente/Código)", lista_gruas_fisicas, key=f"id_fis_{key}", index=idx_fisica)
                
                up_fotos = st.file_uploader("Fotos Evidencia", type=['png','jpg'], key=f"u_{key}", accept_multiple_files=True)

                p_gancho, cap_tab = 50.0, 5000.0
                if id_eq != "Manual" and not df_specs.empty:
                    m = df_specs[df_specs['identificador'] == id_eq].iloc[0]
                    p_gancho, cap_tab = float(m['peso_gancho_kg']), float(m['capacidad_max_ton'])*1000

                c_b1, c_b2, c_b3 = st.columns(3)
                rig = c_b1.number_input("Aparejos (Kg)", 0.0, 50000.0, float(ed.get("rigging", p_gancho)), step=100.0, key=f"r_{key}")
                rad = c_b2.number_input("Radio (m)", 1.0, 150.0, float(ed.get("radio", 5.0)), step=1.0, key=f"rad_{key}")

                cap_sugerida = float(ed.get("capacidad", cap_tab))
                is_disabled = False
                radios_lmi = []
                caps_lmi = []
                if id_eq != "Manual":
                    try:
                        df_t = obtener_dataframe(db_path, "SELECT radio_m, capacidad_kg FROM tablas_carga_equipos WHERE identificador=? ORDER BY radio_m", (id_eq,))
                    except Exception:
                        df_t = pd.DataFrame(columns=["radio_m", "capacidad_kg"])
                    if not df_t.empty:
                        df_t['radio_m'] = pd.to_numeric(df_t['radio_m'], errors='coerce')
                        df_t['capacidad_kg'] = pd.to_numeric(df_t['capacidad_kg'], errors='coerce')
                        df_t = df_t.sort_values(by='radio_m')

                        radios_lmi = df_t['radio_m'].tolist()
                        caps_lmi = df_t['capacidad_kg'].tolist()

                        df_t_filter = df_t[df_t['radio_m'] >= rad]
                        if not df_t_filter.empty:
                            cap_sugerida = float(df_t_filter.iloc[0]["capacidad_kg"])
                            is_disabled = True
                            # Force Streamlit to update the widget cache since it's disabled.
                            st.session_state[f"ct_{key}"] = cap_sugerida

                ct = c_b3.number_input("Cap. Tabla (Kg)", 0.0, 1000000.0, cap_sugerida, disabled=is_disabled, step=100.0, key=f"ct_{key}")

                st.markdown("**Configuración Aparejos (Rigging)**")
                sel_eslinga = st.selectbox("Seleccionar Elemento del Pañol (Inventario CGT):", lista_eslingas, key=f"sel_esl_{key}", index=0)
                if sel_eslinga != "Ingreso Manual":
                    st.info(f"✅ Elemento Vinculado: {sel_eslinga}")

                c_r1, c_r2, c_r3, c_r4, c_r5 = st.columns(5)
                mat = c_r1.selectbox("Material", list(FACTORES_MATERIAL.keys()), key=f"mat_{key}")
                mod = c_r2.selectbox("Modo", list(FACTORES_MODO.keys()), key=f"m_{key}", index=list(FACTORES_MODO.keys()).index(ed.get("tipo_amarre", "Axial (1.0)")) if ed.get("tipo_amarre") in FACTORES_MODO else 0)
                wll = c_r3.number_input("WLL (Kg)", 100, 100000, int(ed.get("wll_base", 2000)), step=100, key=f"w_{key}", help="Carga Límite de Trabajo")
                ram = c_r4.selectbox("Ramales", [1,2,3,4], index=[1,2,3,4].index(ed.get("ramales", 2)) if ed.get("ramales") in [1,2,3,4] else 1, key=f"rm_{key}")
                ang = c_r5.number_input("Ángulo (°)", 30, 90, int(ed.get("angulo", 60)), step=1, key=f"an_{key}")

                st.markdown("**Accesorios Adicionales (ASME B30.26 / B30.9)**")
                c_acc1, c_acc2 = st.columns(2)
                
                sel_shackle = c_acc1.selectbox("Grillete Lira Seleccionado:", list(TABLA_GRILLETES.keys()), key=f"sh_{key}", index=2)
                shackle_wll = TABLA_GRILLETES[sel_shackle]
                
                dd_factor = 1.0
                if mat == "Estrobo Acero (SF 5:1)":
                    sel_dd = c_acc2.selectbox("Relación D/d (Doblez Pluma/Gancho):", list(TABLA_DD.keys()), key=f"dd_{key}", index=0)
                    dd_factor = TABLA_DD[sel_dd]
                else:
                    c_acc2.info("Doblez D/d no aplica a este material.")

                cap_max_ton_val = 50.0
                if id_eq != "Manual" and not df_specs.empty:
                    m = df_specs[df_specs['identificador'] == id_eq].iloc[0]
                    cap_max_ton_val = float(m['capacidad_max_ton'])

                # Peso operativo real de la grúa (chasis + contrapeso). Se usa para la
                # presión sobre el terreno. Por defecto se estima en 1.0 t/t de capacidad.
                peso_op_default = float(ed.get("peso_operativo_ton", round(cap_max_ton_val, 1)))
                peso_operativo_ton = st.number_input(
                    "Peso operativo de la grúa (Ton)", 1.0, 1500.0, peso_op_default, step=1.0, key=f"pop_{key}",
                    help="Peso real de la grúa con contrapeso (de la ficha técnica). Determina la reacción sobre los estabilizadores."
                )

                return {
                    "id": id_eq, "id_fisico": id_fisico, "rigging": rig, "radio": rad, "capacidad": ct, "elemento_pañol": sel_eslinga,
                    "material": mat, "tipo_amarre": mod, "wll_base": wll, "ramales": ram, "angulo": ang,
                    "dist_p": pct, "is_ok": ck1 and ck2,
                    "lmi_radios": radios_lmi, "lmi_caps": caps_lmi,
                    "shackle_wll": shackle_wll, "dd_factor": dd_factor,
                    "capacidad_max_ton": cap_max_ton_val,
                    "peso_operativo_ton": peso_operativo_ton,
                    "peso_operativo_kg": peso_operativo_ton * 1000.0
                }

        cfg_global = {
            "p_neto": p_neto, "viento": viento, "vela": vela, "viento_max": viento_max,
            "es_tandem": es_tandem, "cg_asim": cg_asim, "d1": d1, "d2": d2,
            "area_vela_m2": area_vela_m2, "pad_ancho": pad_ancho, "pad_largo": pad_largo,
            "limite_suelo": limite_suelo
        }
        cfg_a = gui_setup_equipo("UNIDAD A", "a", dist_a)
        cfg_b = gui_setup_equipo("UNIDAD B", "b", 100.0 - dist_a) if es_tandem else None

        if not cfg_a['is_ok'] or (cfg_b and not cfg_b['is_ok']):
            st.warning("⚠️ Validación Requerida: Confirme el Checklist de seguridad para habilitar el cálculo.")
        else:
            res_a = MotorIngenieriaIzaje.calcular_maniobra(cfg_global, cfg_a)
            res_b = MotorIngenieriaIzaje.calcular_maniobra(cfg_global, cfg_b) if cfg_b else None

            st.markdown("---")
            m_ue = max(res_a['utilizacion'], res_b['utilizacion'] if res_b else 0)
            m_ur = max(res_a['util_rigging'], res_b['util_rigging'] if res_b else 0)
            max_sh = max(res_a['shackle_util'], res_b['shackle_util'] if res_b else 0)
            max_suelo = max(res_a['suelo_util'], res_b['suelo_util'] if res_b else 0)

                                    # --- RESULTADOS PRINCIPALES ---
            st.markdown("### 📊 Indicadores Principales de Operación")
            c_r1, c_r2 = st.columns(2)
            
            with c_r1:
                color_ue = '#10b981' if m_ue <= 75 else ('#eab308' if m_ue <= 100 else '#ef4444')
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid {color_ue};'>
                        <p class='metric-label-cgt'>Utilización de Capacidad (Grúa)</p>
                        <p class='metric-value-cgt' style='color: {color_ue};'>{m_ue:.1f}%</p>
                        <div style='background: #334155; border-radius: 4px; height: 8px; margin-top: 10px;'>
                            <div style='background: {color_ue}; width: {min(m_ue, 100)}%; height: 100%; border-radius: 4px;'></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            with c_r2:
                color_ur = '#10b981' if m_ur <= 75 else ('#eab308' if m_ur <= 100 else '#ef4444')
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid {color_ur};'>
                        <p class='metric-label-cgt'>Estrés del Aparejo (Eslingas)</p>
                        <p class='metric-value-cgt' style='color: {color_ur};'>{m_ur:.1f}%</p>
                        <div style='background: #334155; border-radius: 4px; height: 8px; margin-top: 10px;'>
                            <div style='background: {color_ur}; width: {min(m_ur, 100)}%; height: 100%; border-radius: 4px;'></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            # --- DETALLE AUXILIAR DE SEGURIDAD ---
            st.markdown("### 🛡️ Métricas Auxiliares de Seguridad")
            c_sec1, c_sec2, c_sec3 = st.columns(3)
            
            with c_sec1:
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid #3b82f6;'>
                        <p class='metric-label-cgt'>Fuerza de Viento Dinámica</p>
                        <p class='metric-value-cgt' style='color: #2563eb;'>{res_a['drag_force_kg']:.1f} Kg</p>
                        <p style='margin:5px 0 0 0; font-size:0.8rem; color:#64748b;'>Añadida al gancho por arrastre</p>
                    </div>
                """, unsafe_allow_html=True)
                
            with c_sec2:
                color_sh = '#ef4444' if max_sh > 80 else '#10b981'
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid {color_sh};'>
                        <p class='metric-label-cgt'>Utilización de Grillete</p>
                        <p class='metric-value-cgt' style='color: {color_sh};'>{max_sh:.1f}%</p>
                        <p style='margin:5px 0 0 0; font-size:0.8rem; color:#64748b;'>ASME B30.26 Límite</p>
                    </div>
                """, unsafe_allow_html=True)
                
            with c_sec3:
                color_su = '#ef4444' if max_suelo > 80 else '#10b981'
                st.markdown(f"""
                    <div class='metric-card-cgt' style='border-top: 4px solid {color_su};'>
                        <p class='metric-label-cgt'>Presión sobre el Suelo</p>
                        <p class='metric-value-cgt' style='color: {color_su};'>{res_a['presion_suelo_ton_m2']:.1f} t/m²</p>
                        <p style='margin:5px 0 0 0; font-size:0.8rem; color:#64748b;'>Capacidad suelo: {max_suelo:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)

            status_label, status_class = "OPERACIÓN SEGURA ✅", "status-safe"
            if m_ue > 100 or m_ur > 100 or max_sh > 100 or max_suelo > 100 or viento >= viento_max:
                status_label, status_class = "IZAJE NO AUTORIZADO (NO-GO) ❌", "status-danger"
            elif m_ue > 75 or m_ur > 75 or max_sh > 75 or max_suelo > 75: 
                status_label, status_class = "IZAJE CRÍTICO (REFIERA A SUPERVISIÓN) ⚠️", "status-warning"
            st.markdown(f'<div class="status-badge {status_class}">{status_label}</div>', unsafe_allow_html=True)

            # Gráficos Visuales
            try:
                c_img1, c_img2 = st.columns(2)
                img_diag = draw_rigging_diagram(
                    d1, d2, 
                    angulo=res_a['angulo'], 
                    asimetrico=cg_asim, 
                    tandem=es_tandem,
                    tension_a=res_a['tension'],
                    tension_b=res_b['tension'] if res_b else 0,
                    util_a=res_a['util_rigging'],
                    util_b=res_b['util_rigging'] if res_b else 0,
                    dark_mode=True
                )
                c_img1.image(img_diag, caption="Esquema Dinámico de Fuerzas en Aparejos", use_container_width=True)

                if res_a.get('lmi_radios'):
                    lmi_diag = draw_lmi_chart(res_a['lmi_radios'], res_a['lmi_caps'], res_a['radio'], res_a['bruta_con_viento'], dark_mode=True)
                    if lmi_diag: c_img2.image(lmi_diag, caption="Curva LMI Grúa y Punto Operativo", use_container_width=True)
            except Exception as e: st.caption(f"Diagrama no disponible: {e}")

            obj_final = {
                **cfg_global, 
                "p_neto_total": p_neto, 
                "descripcion": desc, 
                "empresa": client, 
                "tipo_carga": vela, 
                "grua_a": res_a, 
                "grua_b": res_b, 
                "es_critico": (m_ue > 75 or m_ur > 75 or max_sh > 75 or max_suelo > 75)
            }

            ca1, ca2 = st.columns(2)
            try:
                p_bytes = pdf_engine.generar('RIGGING_PLAN', obj_final, LOGO_APP, obtener_logo_cliente(client))
                ca1.download_button("📥 DESCARGAR RIGGING PLAN (PDF)", p_bytes, f"RP_{desc}.pdf", use_container_width=True)
            except Exception as e: ca1.error(f"Error PDF: {e}")

            if ca2.button("💾 GUARDAR EN REGISTRO", use_container_width=True):
                ejecutar_query(db_path, "INSERT INTO historial_rigging_plans (descripcion, responsable, datos_json, empresa_id, contrato_id) VALUES (?,?,?,?,?)",
                             (desc, st.session_state.username, json.dumps(obj_final), filtros.get('empresa_id', 0), filtros.get('contrato_id', 0)), commit=True)
                st.success("Guardado exitosamente.")
                st.rerun()

    with tab_hist:
        st.markdown("### 📋 Archivo Histórico")
        query_h = "SELECT id, fecha, descripcion, responsable, datos_json FROM historial_rigging_plans ORDER BY id DESC"
        df_hist = obtener_dataframe(db_path, query_h)
        
        if df_hist.empty: 
            st.info("No hay registros previos.")
        else:
            # Habilitar exportación de historial a Excel/CSV
            tabular_data = []
            for _, r in df_hist.iterrows():
                try:
                    d = json.loads(r['datos_json'])
                    tabular_data.append({
                        "ID Plan": r['id'],
                        "Fecha": r['fecha'],
                        "Descripción": r['descripcion'],
                        "Solicitante": r['responsable'],
                        "Peso Neto Carga (Kg)": d.get("p_neto_total", 0),
                        "Viento (Km/h)": d.get("viento", 0),
                        "Área Vela (m²)": d.get("area_vela_m2", 0),
                        "Esquema": "Tándem" if d.get("es_tandem") else "Simple",
                        "Utilización Grúa A (%)": d.get("grua_a", {}).get("utilizacion", 0),
                        "Utilización Grúa B (%)": d.get("grua_b", {}).get("utilizacion", 0) if d.get("es_tandem") else "N/A",
                        "Estrés Aparejo A (%)": d.get("grua_a", {}).get("util_rigging", 0),
                        "Tensión Ramal A (Kg)": d.get("grua_a", {}).get("tension", 0),
                        "Estrés Grillete A (%)": d.get("grua_a", {}).get("shackle_util", 0),
                        "Presión Terreno A (t/m²)": d.get("grua_a", {}).get("presion_suelo_ton_m2", 0),
                    })
                except Exception:
                    pass
            
            if tabular_data:
                df_export = pd.DataFrame(tabular_data)
                csv_bytes = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 EXPORTAR HISTORIAL COMPLETO (CSV)",
                    csv_bytes,
                    "Historial_Rigging_Plans.csv",
                    "text/csv",
                    use_container_width=True
                )
                st.markdown("---")

            # Mostrar registros históricos expandibles
            for _, r in df_hist.head(20).iterrows():
                with st.expander(f"📦 #{r['id']} | {r['descripcion']} | {r['responsable']}"):
                    d_js = json.loads(r['datos_json'])
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("🔄 Cargar Configuración", key=f"cl_{r['id']}"):
                        st.session_state.clone_data = d_js
                        st.rerun()
                    if col_h2.button("🗑️ Eliminar Plan", key=f"dl_{r['id']}"):
                        ejecutar_query(db_path, "DELETE FROM historial_rigging_plans WHERE id = ?", (r['id'],), commit=True)
                        st.rerun()

    with tab_equipos:
        st.markdown("### 🛠️ Registro y Gestión de Equipos de Izaje")
        
        # 1. Mostrar listado de equipos actualmente registrados
        st.markdown("#### Equipos Enrolados")
        df_eq_specs = obtener_dataframe(db_path, "SELECT * FROM especificaciones_equipos")
        if df_eq_specs.empty:
            st.info("No hay equipos personalizados registrados.")
        else:
            for _, eq in df_eq_specs.iterrows():
                # Get LMI load chart points for each crane
                df_eq_lmi = obtener_dataframe(db_path, "SELECT radio_m, capacidad_kg FROM tablas_carga_equipos WHERE identificador=? ORDER BY radio_m", (eq['identificador'],))
                lmi_points_str = ", ".join([f"{r}m: {c:,.0f}Kg" for r, c in zip(df_eq_lmi['radio_m'], df_eq_lmi['capacidad_kg'])]) if not df_eq_lmi.empty else "Sin tabla LMI"
                
                with st.container(border=True):
                    col_det1, col_det2 = st.columns([4, 1])
                    with col_det1:
                        st.markdown(f"**🏗️ {eq['identificador']}**")
                        st.markdown(f"* **Capacidad Máxima:** {eq['capacidad_max_ton']} Ton | **Peso del Gancho:** {eq['peso_gancho_kg']} Kg")
                        st.caption(f"**Curva LMI:** {lmi_points_str}")
                    with col_det2:
                        # Botón para eliminar el equipo y su tabla LMI
                        if st.button("🗑️ Eliminar", key=f"del_eq_{eq['id']}"):
                            ejecutar_query(db_path, "DELETE FROM especificaciones_equipos WHERE identificador = ?", (eq['identificador'],), commit=True)
                            ejecutar_query(db_path, "DELETE FROM tablas_carga_equipos WHERE identificador = ?", (eq['identificador'],), commit=True)
                            st.success(f"Equipo {eq['identificador']} eliminado.")
                            st.rerun()

        st.markdown("---")
        st.markdown("#### ➕ Registrar Nuevo Equipo / Camión Pluma")
        
        with st.form("form_nuevo_equipo", clear_on_submit=True):
            col_in1, col_in2, col_in3 = st.columns(3)
            nuevo_id = col_in1.text_input("Identificador del Equipo (ej: Camión Pluma Fassi 45T)", placeholder="Fassi F455XP")
            nuevo_gancho = col_in2.number_input("Peso Propio del Gancho (Kg)", 1.0, 5000.0, 150.0, step=100.0)
            nueva_cap_max = col_in3.number_input("Capacidad Máxima de Tabla (Ton)", 0.5, 1000.0, 45.0, step=0.1)
            
            st.markdown("**Configurar Tabla de Carga LMI (Radio en metros vs Capacidad en Kilogramos)**")
            st.markdown("<small>Agrega filas para definir las capacidades por metros de extendida de la pluma.</small>", unsafe_allow_html=True)
            
            # Tabla interactiva st.data_editor para definir la curva LMI
            default_lmi_data = pd.DataFrame([
                {"Radio (m)": 2.0, "Capacidad (Kg)": 8000.0},
                {"Radio (m)": 4.0, "Capacidad (Kg)": 4500.0},
                {"Radio (m)": 6.0, "Capacidad (Kg)": 3000.0},
                {"Radio (m)": 8.0, "Capacidad (Kg)": 2000.0},
            ])
            edited_lmi = st.data_editor(
                default_lmi_data,
                column_config={
                    "Radio (m)": st.column_config.NumberColumn(
                        "Radio (m)",
                        min_value=0.1,
                        max_value=150.0,
                        step=1.0,
                        format="%.1f m"
                    ),
                    "Capacidad (Kg)": st.column_config.NumberColumn(
                        "Capacidad (Kg)",
                        min_value=0.0,
                        max_value=1000000.0,
                        step=100.0,
                        format="%d Kg"
                    )
                },
                num_rows="dynamic",
                use_container_width=True,
                key="editor_tabla_lmi"
            )
            
            submit_eq = st.form_submit_button("💾 REGISTRAR Y GUARDAR EQUIPO", use_container_width=True)
            
            if submit_eq:
                if not nuevo_id.strip():
                    st.error("Por favor, ingresa un identificador válido para el equipo.")
                elif edited_lmi.empty:
                    st.error("Debes agregar al menos un punto a la tabla LMI.")
                else:
                    try:
                        # Guardar especificaciones
                        ejecutar_query(db_path, "INSERT INTO especificaciones_equipos (identificador, peso_gancho_kg, capacidad_max_ton, empresa_id) VALUES (?,?,?,?)",
                                     (nuevo_id.strip(), nuevo_gancho, nueva_cap_max, st.session_state.empresa_id), commit=True)
                        
                        # Guardar puntos LMI
                        for _, row in edited_lmi.iterrows():
                            rad_val = float(row["Radio (m)"])
                            cap_val = float(row["Capacidad (Kg)"])
                            ejecutar_query(db_path, "INSERT INTO tablas_carga_equipos (identificador, radio_m, capacidad_kg) VALUES (?,?,?)",
                                         (nuevo_id.strip(), rad_val, cap_val), commit=True)
                                         
                        st.success(f"¡Equipo '{nuevo_id}' registrado exitosamente con su tabla de carga!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar equipo (el nombre debe ser único): {e}")

if __name__ == "__main__":
    st.set_page_config(
        page_title="Rigger 360° | Ingeniería de Izaje",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Inicializar Base de Datos local
    init_db()
    
    # Inicializar Session State con valores por defecto para omitir controles administrativos
    if 'role' not in st.session_state:
        st.session_state.role = "Global Admin"
    if 'empresa_id' not in st.session_state:
        st.session_state.empresa_id = 0
    if 'username' not in st.session_state:
        st.session_state.username = "Ingeniero Rigger"
    if 'filtros' not in st.session_state:
        st.session_state.filtros = {"empresa_nom": "General", "empresa_id": 0, "contrato_id": 0}
    if 'clone_data' not in st.session_state:
        st.session_state.clone_data = {}
        
    # Ejecutar renderizado principal directamente sin barra lateral de prueba
    render_calculadora_izaje(DB_FILE, st.session_state.filtros)
