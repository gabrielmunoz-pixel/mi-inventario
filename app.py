import streamlit as st
import pandas as pd
import re
import json
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error de conexión con Supabase.")
    st.stop()

# --- 2. GESTIÓN DE SESIÓN ---
def sync_session():
    params = st.query_params
    if "user_data" in params and "auth_user" not in st.session_state:
        try: st.session_state.auth_user = json.loads(params["user_data"])
        except: pass
    if "auth_user" in st.session_state:
        st.query_params["user_data"] = json.dumps(st.session_state.auth_user)

def logout():
    if "auth_user" in st.session_state: del st.session_state.auth_user
    if "carritos" in st.session_state: st.session_state.carritos = {}
    st.query_params.clear()
    st.rerun()

# --- 3. DISEÑO VISUAL (GRID INDESTRUCTIBLE) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}
    .stMarkdown p, label p, .stHeader h1, .stHeader h2, .stExpander p, .stAlert p {{ color: #FFFFFF !important; }}
    
    /* Botones generales */
    div.stButton > button {{ 
        background-color: #FFCC00 !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        border-radius: 10px !important;
    }}

    /* --- CONTENEDOR DE CALCULADORA --- */
    /* Forzamos que el contenido del expander no tenga márgenes locos */
    [data-testid="stExpander"] [data-testid="stVerticalBlock"] {{
        gap: 0rem !important;
    }}

    /* ESTILO DE LA MATRIZ 4x4 USANDO CSS GRID */
    .grid-calculadora {{
        display: grid !important;
        grid-template-columns: repeat(4, 1fr) !important; /* 4 columnas iguales siempre */
        gap: 8px !important;
        width: 100% !important;
        margin: 0 auto !important;
    }}

    /* Estilo de los botones dentro del Grid */
    .grid-calculadora button {{
        aspect-ratio: 1 / 1 !important;
        width: 100% !important;
        height: auto !important;
        font-size: 22px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    .btn-num button {{ background-color: #FFCC00 !important; color: #000000 !important; }}
    .btn-op button {{ background-color: #333333 !important; color: #FFCC00 !important; border: 1px solid #FFCC00 !important; }}
    .btn-clear button {{ background-color: #440000 !important; color: white !important; }}

    /* Botón LISTO más grande abajo */
    .calc-footer {{
        margin-top: 15px;
        display: flex;
        gap: 10px;
    }}
    
    .nav-active > div > button {{ background-color: #FFFFFF !important; border: 2px solid #FFCC00 !important; }}
    .red-btn > div > button {{ background-color: #DD0000 !important; color: white !important; }}
    .green-btn > div > button {{ background-color: #28a745 !important; color: white !important; }}
    .user-info {{ font-family: monospace; color: #FFCC00; font-size: 12px; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNCIONES LÓGICAS ---
def get_locales_map():
    try:
        res = supabase.table("locales").select("id, nombre").execute().data
        return {l['nombre']: l['id'] for l in res} if res else {}
    except: return {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

def obtener_stock_dict(local_id):
    try:
        res = supabase.table("movimientos_inventario").select("id_producto, cantidad").eq("id_local", local_id).execute().data
        if not res: return {}
        df = pd.DataFrame(res)
        return df.groupby("id_producto")["cantidad"].sum().to_dict()
    except: return {}

# --- 5. COMPONENTE CALCULADORA (REDiseñado con DIVs de GRID) ---
def calculadora_basica():
    if "calc_val" not in st.session_state: st.session_state.calc_val = ""
    
    # Pantalla de la calculadora
    st.markdown(f"""
        <div style="background:#1e1e1e; color:#00ff00; padding:15px; border-radius:10px; 
        text-align:right; font-family:monospace; font-size:32px; margin-bottom:15px; border:2px solid #333;">
            {st.session_state.calc_val if st.session_state.calc_val else "0"}
        </div>
    """, unsafe_allow_html=True)
    
    # Definición de botones en orden de grid
    botones = [
        ("7", "num"), ("8", "num"), ("9", "num"), ("/", "op"),
        ("4", "num"), ("5", "num"), ("6", "num"), ("*", "op"),
        ("1", "num"), ("2", "num"), ("3", "num"), ("-", "op"),
        ("0", "num"), (".", "num"), ("C", "clear"), ("+", "op")
    ]
    
    # Creamos el contenedor Grid
    st.markdown('<div class="grid-calculadora">', unsafe_allow_html=True)
    # IMPORTANTE: Usamos columnas vacías de Streamlit solo como anclaje, 
    # pero el CSS Grid las obligará a comportarse.
    cols = st.columns(4) 
    
    for i, (label, tipo) in enumerate(botones):
        # Usamos el operador módulo para rotar entre las 4 columnas
        with cols[i % 4]:
            st.markdown(f'<div class="btn-{tipo}">', unsafe_allow_html=True)
            if st.button(label, key=f"grid_btn_{label}_{i}"):
                if label == "C": st.session_state.calc_val = ""
                else: st.session_state.calc_val += label
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Botones de acción inferior
    st.markdown('<div class="calc-footer">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ Borrar", use_container_width=True):
            st.session_state.calc_val = st.session_state.calc_val[:-1]
            st.rerun()
    with c2:
        if st.button("LISTO", type="primary", use_container_width=True):
            try:
                if st.session_state.calc_val:
                    st.session_state.resultado_calc = float(eval(st.session_state.calc_val))
                    st.session_state.show_calc = False
                    st.session_state.calc_val = ""
                    st.rerun()
            except: st.error("Error")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. PANTALLAS --- (Todo igual que tu original)
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario")
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    if 'show_calc' not in st.session_state: st.session_state.show_calc = False
    if 'resultado_calc' not in st.session_state: st.session_state.resultado_calc = 0.0

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    opciones = sorted(list(prod_map.keys()))
    
    sel = st.selectbox("Selecciona o busca el producto:", [""] + opciones)
    
    if sel:
        p = prod_map[sel]
        c1, c2, c3 = st.columns([2, 2, 0.6])
        with c1: ubi = st.selectbox("Ubicación:", ["Bodega", "Frío", "Cocina", "Producción"])
        with c2: 
            cant = st.number_input("Cantidad:", min_value=0.0, step=1.0, value=float(st.session_state.resultado_calc))
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧮"):
                st.session_state.show_calc = not st.session_state.show_calc
                st.rerun()

        if st.session_state.show_calc:
            with st.expander("Panel de Cálculo", expanded=True):
                calculadora_basica()

        if st.button("Añadir a inventario"):
            st.session_state.carritos[user_key].append({
                "id_producto": p['id'], "Producto": p['nombre'], "Ubicación": ubi, 
                "Cantidad": float(cant), "Formato": p['formato_medida'], 
                "Factor": extraer_valor_formato(p['formato_medida'])
            })
            st.toast(f"✅ Añadido: {p['nombre']}")
            st.session_state.resultado_calc = 0.0
            st.rerun()

    if st.session_state.carritos[user_key]:
        df = pd.DataFrame(st.session_state.carritos[user_key])
        ed = st.data_editor(df, column_config={"id_producto": None, "Factor": None}, use_container_width=True)
        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("🚀 FINALIZAR"):
                for r in ed.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({
                        "id_local": local_id, "id_producto": r['id_producto'], 
                        "cantidad": r['Cantidad']*r['Factor'], "tipo_movimiento": "AJUSTE", 
                        "ubicacion": r['Ubicación']
                    }).execute()
                st.success("Guardado"); st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR"): st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla(local_id):
    st.header("📊 Reportes")
    t1, t2 = st.tabs(["🕒 Historial", "📦 Stock Actual"])
    try:
        query = supabase.table("movimientos_inventario").select("*, productos_maestro(sku, nombre, formato_medida)").eq("id_local", local_id).execute().data
        if not query: st.warning("No hay registros"); return
        df = pd.json_normalize(query)
        with t1:
            st.dataframe(df[['fecha_hora', 'productos_maestro.sku', 'productos_maestro.nombre', 'tipo_movimiento', 'cantidad']], use_container_width=True)
        with t2:
            df_s = df.groupby(['productos_maestro.sku', 'productos_maestro.nombre', 'productos_maestro.formato_medida'])['cantidad'].sum().reset_index()
            df_s['Factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
            df_s['Stock'] = (df_s['cantidad'] / df_s['Factor']).round(2)
            st.dataframe(df_s[['productos_maestro.sku', 'productos_maestro.nombre', 'Stock']], use_container_width=True)
    except Exception as e: st.error(str(e))

def admin_maestro(local_id):
    st.header("⚙️ Maestro de Productos")
    with st.expander("📤 Carga Masiva (Excel / CSV)"):
        up = st.file_uploader("Subir archivo", type=["xlsx", "csv"])
        if up and st.button("Procesar"):
            try:
                df_up = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                mapeo = {"Número de artículo": "sku", "Descripción del artículo": "nombre", "Categoria": "categoria"}
                df_up = df_up.rename(columns=mapeo)
                if 'formato_medida' not in df_up.columns: df_up['formato_medida'] = "1 unidad"
                columnas_validas = ['sku', 'nombre', 'categoria', 'formato_medida']
                df_final = df_up[[c for c in columnas_validas if c in df_up.columns]]
                supabase.table("productos_maestro").upsert(df_final.to_dict(orient='records'), on_conflict="sku").execute()
                st.success("✅ Éxito"); st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        st_dict = obtener_stock_dict(local_id)
        df_m = pd.DataFrame(res)
        df_m['Stock Actual'] = df_m.apply(lambda r: round(st_dict.get(r['id'], 0) / extraer_valor_formato(r['formato_medida']), 2), axis=1)
        ed = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar Cambios"):
            for i, row in ed.iterrows():
                supabase.table("productos_maestro").upsert({"id": row['id'], "sku": row['sku'], "nombre": row['nombre'], "categoria": row['categoria'], "formato_medida": row['formato_medida']}).execute()
            st.success("Guardado"); st.rerun()

def admin_usuarios(locales):
    st.header("👤 Usuarios")
    if 'u_act' not in st.session_state: st.session_state.u_act = None
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("Admin"): st.session_state.u_act = "admin"
    with c2: 
        if st.button("Staff"): st.session_state.u_act = "staff"
    with c3: 
        if st.button("Editar"): st.session_state.u_act = "edit"
    
    if st.session_state.u_act in ["admin", "staff"]:
        with st.form("U"):
            n = st.text_input("Nombre"); u = st.text_input("User"); p = st.text_input("Pass")
            l_id = 1
            if st.session_state.u_act == "staff":
                l_sel = st.selectbox("Sede", list(locales.keys())); l_id = locales[l_sel]
            if st.form_submit_button("Crear"):
                rol = "Admin" if st.session_state.u_act == "admin" else "Staff"
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": l_id, "usuario": u, "clave": p, "rol": rol}, on_conflict="usuario").execute()
                st.session_state.u_act = None; st.rerun()

# --- 7. MAIN ---
def main():
    sync_session()
    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login"):
                u = st.text_input("Usuario"); p = st.text_input("Clave", type="password")
                if st.form_submit_button("INGRESAR"):
                    if u.lower() == "admin" and p == "654321.": 
                        st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}; st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        st.session_state.auth_user = {"user": u, "role": res[0]['rol'], "local": res[0]['id_local']}; st.rerun()
                    else: st.error("Fallo")
        return

    user = st.session_state.auth_user
    ld = get_locales_map(); li = {v: k for k, v in ld.items()}
    if 'opt' not in st.session_state: st.session_state.opt = "📋 Ingreso"
    
    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        idx = list(ld.keys()).index(li.get(user['local'], list(ld.keys())[0]))
        user['local'] = ld[st.sidebar.selectbox("Sede:", list(ld.keys()), index=idx)]
    
    st.sidebar.markdown(f'<div class="user-info">Sede: {li.get(user["local"], "N/A")}</div>', unsafe_allow_html=True)
    opts = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    for o in opts:
        act = "nav-active" if st.session_state.opt == o else ""
        st.sidebar.markdown(f'<div class="{act}">', unsafe_allow_html=True)
        if st.sidebar.button(o): st.session_state.opt = o; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    if st.sidebar.button("Salir"): logout()
    
    if st.session_state.opt == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": reportes_pantalla(user['local'])
    elif st.session_state.opt == "👤 Usuarios": admin_usuarios(ld)
    elif st.session_state.opt == "⚙️ Maestro": admin_maestro(user['local'])

if __name__ == "__main__": main()
