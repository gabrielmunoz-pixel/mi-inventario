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

# --- 2. GESTIÓN DE SESIÓN PERSISTENTE Y LOGOUT ---
def sync_session():
    params = st.query_params
    if "user_data" in params and "auth_user" not in st.session_state:
        try:
            st.session_state.auth_user = json.loads(params["user_data"])
        except:
            pass
    if "auth_user" in st.session_state:
        st.query_params["user_data"] = json.dumps(st.session_state.auth_user)

def logout():
    if "auth_user" in st.session_state:
        del st.session_state.auth_user
    if "carritos" in st.session_state:
        st.session_state.carritos = {}
    st.query_params.clear()
    st.rerun()

# --- 3. DISEÑO VISUAL (OPTIMIZADO PARA MÓVIL Y MAESTRO) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}

    /* TEXTOS GENERALES EN BLANCO */
    div[data-testid="stWidgetLabel"] p, label, .stMarkdown p, .stHeader h1, .stHeader h2, .stExpander p {{ 
        color: #FFFFFF !important; 
        -webkit-text-fill-color: #FFFFFF !important;
    }}
    
    .stAlert p, .stWarning p {{ color: #FFFFFF !important; }}

    /* INPUTS (FONDO BLANCO, TEXTO NEGRO) */
    .stTextInput>div>div>input {{ 
        background-color: #FFFFFF !important; 
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }}

    /* FIX MAESTRO: Selectores y menús de tabla con texto negro */
    div[data-baseweb="select"] > div, div[role="listbox"], div[data-testid="stDataFrame"] * {{ 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
    }}
    li[role="option"], div[role="option"], div[data-baseweb="popover"] * {{ 
        color: #000000 !important; 
    }}

    /* BOTONES ALEMAN EXPERTO */
    div.stButton > button {{
        background-color: #FFCC00 !important;
        color: #000000 !important;
        font-weight: bold !important;
        min-width: 170.86px !important;
    }}
    div.stButton > button p {{ color: #000000 !important; }}
    
    .nav-active > div > button {{ background-color: #FFFFFF !important; border: 2px solid #FFCC00 !important; }}
    .red-btn > div > button {{ background-color: #DD0000 !important; color: white !important; }}
    .green-btn > div > button {{ background-color: #28a745 !important; color: white !important; }}
    
    .user-info {{ font-family: monospace; color: #FFCC00; font-size: 12px; }}
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

# --- 5. PANTALLAS ---
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario Mensual")
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    
    try:
        res = supabase.table("productos_maestro").select("*").execute().data
    except: return

    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    busqueda = st.text_input("🔍 Buscar producto:", placeholder="Escribe el nombre...")
    opciones = [o for o in prod_map.keys() if busqueda.lower() in o.lower()]
    sel = st.selectbox("Selecciona producto:", [""] + opciones)
    
    if sel:
        p = prod_map[sel]
        c1, c2 = st.columns(2)
        with c1: ubi = st.selectbox("Ubicación:", ["Bodega", "Frío", "Cocina", "Producción"])
        with c2: cant = st.number_input(f"Cantidad:", min_value=0.0, step=1.0)
        if st.button("Añadir"):
            st.session_state.carritos[user_key].append({
                "id_producto": p['id'], "Producto": p['nombre'], "Ubicación": ubi, 
                "Cantidad": float(cant), "Formato": p['formato_medida'], 
                "Factor": extraer_valor_formato(p['formato_medida'])
            })
            st.toast(f"✅ Añadido: {p['nombre']}")

    if st.session_state.carritos[user_key]:
        df = pd.DataFrame(st.session_state.carritos[user_key])
        ed = st.data_editor(df, column_config={"id_producto": None, "Factor": None, "Producto": st.column_config.TextColumn(disabled=True)}, use_container_width=True)
        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("Finalizar"):
                try:
                    for r in ed.to_dict(orient='records'):
                        supabase.table("movimientos_inventario").insert({
                            "id_local": local_id, "id_producto": r['id_producto'], 
                            "cantidad": r['Cantidad']*r['Factor'], "tipo_movimiento": "AJUSTE", 
                            "ubicacion": r['Ubicación']
                        }).execute()
                    st.success("✅ Guardado correctamente")
                    st.session_state.carritos[user_key] = []; st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("Borrar"): st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla(local_id):
    st.header("📊 Reportes de Inventario")
    t1, t2 = st.tabs(["🕒 Historial", "📦 Stock Local"])
    try:
        query = supabase.table("movimientos_inventario").select("*, productos_maestro(nombre, formato_medida)").eq("id_local", local_id).execute().data
        if not query:
            st.warning("Sin datos."); return
        df = pd.json_normalize(query)
        with t1:
            st.dataframe(df[['fecha_hora', 'productos_maestro.nombre', 'tipo_movimiento', 'cantidad', 'ubicacion']], use_container_width=True)
        with t2:
            df_s = df.groupby(['productos_maestro.nombre', 'productos_maestro.formato_medida'])['cantidad'].sum().reset_index()
            df_s['Factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
            df_s['Stock Actual'] = (df_s['cantidad'] / df_s['Factor']).round(2)
            st.dataframe(df_s[['productos_maestro.nombre', 'productos_maestro.formato_medida', 'Stock Actual']], use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

def admin_maestro():
    st.header("⚙️ Maestro de Productos")
    with st.expander("📤 Carga Masiva"):
        up = st.file_uploader("Subir Excel/CSV", type=["xlsx", "csv"])
        if up and st.button("Procesar"):
            try:
                df_up = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                supabase.table("productos_maestro").upsert(df_up.to_dict(orient='records')).execute()
                st.success("Carga exitosa"); st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        ed = st.data_editor(pd.DataFrame(res), num_rows="dynamic", use_container_width=True)
        if st.button("Guardar Cambios"):
            supabase.table("productos_maestro").upsert(ed.to_dict(orient='records')).execute()
            st.rerun()

def admin_usuarios(locales):
    st.header("👤 Usuarios")
    if 'u_act' not in st.session_state: st.session_state.u_act = None
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("Admin"): st.session_state.u_act = "admin"
    with c2: 
        if st.button("Staff"): st.session_state.u_act = "staff"
    with c3: 
        if st.button("Edit"): st.session_state.u_act = "edit"
    if st.session_state.u_act in ["admin", "staff"]:
        with st.form("UF"):
            n = st.text_input("Nombre"); u = st.text_input("Usuario"); p = st.text_input("Clave")
            l_id = 1
            if st.session_state.u_act == "staff":
                l_sel = st.selectbox("Sede", list(locales.keys())); l_id = locales[l_sel]
            if st.form_submit_button("Guardar"):
                rol = "Admin" if st.session_state.u_act == "admin" else "Staff"
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": l_id, "usuario": u, "clave": p, "rol": rol}, on_conflict="usuario").execute()
                st.session_state.u_act = None; st.rerun()
    elif st.session_state.u_act == "edit":
        res = supabase.table("usuarios_sistema").select("*").execute().data
        if res:
            u_sel = st.selectbox("Seleccione", [x['usuario'] for x in res])
            curr = next(x for x in res if x['usuario'] == u_sel)
            with st.form("EF"):
                en = st.text_input("Nombre", value=curr['nombre_apellido']); ep = st.text_input("Clave", value=curr['clave'])
                if st.form_submit_button("Actualizar"):
                    supabase.table("usuarios_sistema").update({"nombre_apellido": en, "clave": ep}).eq("usuario", u_sel).execute(); st.rerun()
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("Eliminar"):
                supabase.table("usuarios_sistema").delete().eq("usuario", u_sel).execute(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MAIN ---
def main():
    sync_session()
    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login"):
                u = st.text_input("Usuario"); p = st.text_input("Clave", type="password")
                if st.form_submit_button("Ingresar"):
                    if u.lower() == "admin" and p == "654321.": 
                        st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}; st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        st.session_state.auth_user = {"user": u, "role": res[0]['rol'], "local": res[0]['id_local']}; st.rerun()
                    else: st.error("Acceso denegado.")
        return
    user = st.session_state.auth_user
    ld = get_locales_map(); li = {v: k for k, v in ld.items()}
    if 'opt' not in st.session_state: st.session_state.opt = "📋 Ingreso"
    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        idx = list(ld.keys()).index(li.get(user['local'], list(ld.keys())[0]))
        user['local'] = ld[st.sidebar.selectbox("Sede:", list(ld.keys()), index=idx)]
    st.sidebar.markdown(f'<div class="user-info">Usuario : {user["user"]}\nSede    : {li.get(user["local"], "N/A")}</div>', unsafe_allow_html=True)
    opts = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    for o in opts:
        act = "nav-active" if st.session_state.opt == o else ""
        st.sidebar.markdown(f'<div class="{act}">', unsafe_allow_html=True)
        if st.sidebar.button(o): st.session_state.opt = o; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    if st.sidebar.button("Cerrar Sesión"): logout()
    
    if st.session_state.opt == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": reportes_pantalla(user['local'])
    elif st.session_state.opt == "👤 Usuarios": admin_usuarios(ld)
    elif st.session_state.opt == "⚙️ Maestro": admin_maestro()

if __name__ == "__main__": main()
