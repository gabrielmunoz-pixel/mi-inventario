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

# --- 2. GESTIÓN DE SESIÓN PERSISTENTE (URL PARAMS) ---
def sync_session():
    # Recuperar de la URL si no está en session_state
    params = st.query_params
    if "user_data" in params and "auth_user" not in st.session_state:
        try:
            st.session_state.auth_user = json.loads(params["user_data"])
        except:
            pass
    
    # Actualizar URL si hay cambio en session_state
    if "auth_user" in st.session_state:
        st.query_params["user_data"] = json.dumps(st.session_state.auth_user)
    else:
        if "user_data" in st.query_params:
            del st.query_params["user_data"]

# --- 3. DISEÑO VISUAL (OPTIMIZADO MÓVIL + AE STYLE) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; color: #FFFFFF; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}
    
    /* Visibilidad Menú Móvil */
    [data-testid="stSidebarCollapsedControl"] {{
        color: #FFCC00 !important;
        background-color: rgba(255, 204, 0, 0.2) !important;
        border-radius: 8px !important;
    }}

    /* Tabla Compacta para Celulares */
    [data-testid="stDataEditor"] div {{ font-size: 11px !important; }}
    
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab {{ color: #FFFFFF !important; }}
    
    /* BOTONES: 170.86px x 32.59px */
    div.stButton > button {{
        background-color: #FFCC00 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 1px solid #FFCC00 !important;
        min-width: 170.86px !important;
        max-width: 170.86px !important;
        height: 32.59px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        margin-bottom: -18px !important;
        border-radius: 4px;
    }}
    
    div.stButton > button p {{ color: #000000 !important; font-size: 13px !important; margin: 0 !important; }}
    [data-testid="stVerticalBlock"] > div:has(button) {{ gap: 0.5rem !important; }}

    .nav-active > div > button {{ background-color: #FFFFFF !important; border: 2px solid #FFCC00 !important; }}
    .red-btn > div > button {{ background-color: #DD0000 !important; border-color: #DD0000 !important; }}
    .red-btn > div > button p {{ color: #FFFFFF !important; }}
    .green-btn > div > button {{ background-color: #28a745 !important; border-color: #28a745 !important; }}
    .green-btn > div > button p {{ color: #FFFFFF !important; }}

    /* Cartel de Aviso (Toast) */
    [data-testid="stToast"] {{ background-color: #FFCC00 !important; border: 1px solid #000000 !important; }}
    [data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{ color: #000000 !important; font-weight: bold !important; }}
    [data-testid="stToast"] button {{ color: #000000 !important; }}

    .stSelectbox div[data-baseweb="select"] > div {{ background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }}
    .stTextInput>div>div>input {{ background-color: #1A1A1A; color: white; border: 1px solid #333; }}
    h1, h2, h3 {{ color: #FFCC00 !important; }}
    
    .user-info {{ font-family: monospace; white-space: pre; color: #FFCC00; font-size: 12px; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNCIONES DE LÓGICA ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

# --- 5. PANTALLAS ---

def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Inventario")
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    busqueda = st.text_input("🔍 Buscar:", placeholder="Producto...")
    opciones = [o for o in prod_map.keys() if busqueda.lower() in o.lower()]
    sel = st.selectbox("Producto:", [""] + opciones)
    
    if sel:
        p = prod_map[sel]
        c1, c2 = st.columns(2)
        with c1: ubi = st.selectbox("Ubi:", ["Bodega", "Frío", "Cocina", "Producción"])
        with c2: cant = st.number_input(f"Cant:", min_value=0.0, step=1.0)
        if st.button("Añadir"):
            st.session_state.carritos[user_key].append({
                "id_producto": p['id'], "Producto": p['nombre'], "Ubicación": ubi, 
                "Cantidad": float(cant), "Formato": p['formato_medida'], 
                "Factor": extraer_valor_formato(p['formato_medida'])
            })
            st.toast(f"Ok: {p['nombre']}")

    if st.session_state.carritos[user_key]:
        df = pd.DataFrame(st.session_state.carritos[user_key])
        ed = st.data_editor(df, column_config={"id_producto": None, "Factor": None, "Producto": st.column_config.TextColumn(disabled=True)}, use_container_width=True)
        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("Finalizar"):
                sid = f"SES-{user_key[:3].upper()}-{datetime.now().strftime('%m%d%H%M')}"
                for r in ed.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({"id_local": local_id, "id_producto": r['id_producto'], "cantidad": r['Cantidad']*r['Factor'], "tipo_movimiento": "CONTEO", "ubicacion": r['Ubicación'], "notas": sid}).execute()
                st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("Borrar"): st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def admin_usuarios(locales):
    st.header("👤 Usuarios")
    if 'u_act' not in st.session_state: st.session_state.u_act = None
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("Crear Admin"): st.session_state.u_act = "admin"
    with c2: 
        if st.button("Crear Staff"): st.session_state.u_act = "staff"
    with c3: 
        if st.button("Modificar"): st.session_state.u_act = "edit"
    
    st.divider()
    if st.session_state.u_act in ["admin", "staff"]:
        with st.form("UserF"):
            n = st.text_input("Nombre"); u = st.text_input("Usuario"); p = st.text_input("Clave")
            l_id = 1
            if st.session_state.u_act == "staff":
                l_sel = st.selectbox("Sede", list(locales.keys())); l_id = locales[l_sel]
            if st.form_submit_button("Guardar"):
                rol = "Admin" if st.session_state.u_act == "admin" else "Staff"
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": l_id, "usuario": u, "clave": p, "rol": rol}, on_conflict="usuario").execute()
                st.success("Listo."); st.session_state.u_act = None; st.rerun()
    elif st.session_state.u_act == "edit":
        res = supabase.table("usuarios_sistema").select("*").execute().data
        if res:
            u_sel = st.selectbox("Seleccione", [x['usuario'] for x in res])
            curr = next(x for x in res if x['usuario'] == u_sel)
            with st.form("EditF"):
                en = st.text_input("Nombre", value=curr['nombre_apellido']); ep = st.text_input("Clave", value=curr['clave'])
                if st.form_submit_button("Actualizar"):
                    supabase.table("usuarios_sistema").update({"nombre_apellido": en, "clave": ep}).eq("usuario", u_sel).execute(); st.rerun()
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("Eliminar Usuario"):
                supabase.table("usuarios_sistema").delete().eq("usuario", u_sel).execute(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MAIN ---
def main():
    sync_session() # Mantener sesión viva

    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login"):
                u = st.text_input("Usuario"); p = st.text_input("Clave", type="password")
                if st.form_submit_button("Ingresar"):
                    if u.lower() == "admin" and p == "654321.": 
                        st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}
                        st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        st.session_state.auth_user = {"user": u, "role": res[0]['rol'], "local": res[0]['id_local']}
                        st.rerun()
                    else: st.error("Error.")
        return

    user = st.session_state.auth_user
    ld = get_locales_map(); li = {v: k for k, v in ld.items()}
    if 'opt' not in st.session_state: st.session_state.opt = "📋 Ingreso"

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        user['local'] = ld[st.sidebar.selectbox("Sede:", list(ld.keys()), index=list(ld.keys()).index(li.get(user['local'], list(ld.keys())[0])))]
    
    st.sidebar.markdown(f'<div class="user-info">Usuario : {user["user"]}\nSede    : {li.get(user["local"], "N/A")}</div>', unsafe_allow_html=True)
    st.sidebar.divider()

    opts = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    for o in opts:
        act = "nav-active" if st.session_state.opt == o else ""
        st.sidebar.markdown(f'<div class="{act}">', unsafe_allow_html=True)
        if st.sidebar.button(o): st.session_state.opt = o; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.divider()
    if st.sidebar.button("Cerrar Sesión"): 
        del st.session_state.auth_user
        st.rerun()

    if st.session_state.opt == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": 
        st.header("📊 Reportes")
        q = supabase.table("movimientos_inventario").select("*, productos_maestro(nombre, formato_medida)").eq("tipo_movimiento", "CONTEO").execute().data
        if q:
            df_r = pd.json_normalize(q)
            ses = st.selectbox("Sesión:", sorted(df_r['notas'].unique().tolist(), reverse=True))
            if ses:
                df_s = df_r[df_r['notas'] == ses].copy()
                df_s['factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
                df_s['Unid'] = (df_s['cantidad'] / df_s['factor']).round(2)
                st.dataframe(df_s[['productos_maestro.nombre', 'ubicacion', 'Unid']], use_container_width=True)
    elif st.session_state.opt == "👤 Usuarios": admin_usuarios(ld)
    elif st.session_state.opt == "⚙️ Maestro":
        st.header("⚙️ Maestro")
        res = supabase.table("productos_maestro").select("*").execute().data
        if res:
            ed = st.data_editor(pd.DataFrame(res), num_rows="dynamic", use_container_width=True)
            if st.button("Guardar Cambios"): supabase.table("productos_maestro").upsert(ed.to_dict(orient='records')).execute(); st.rerun()

if __name__ == "__main__": main()
