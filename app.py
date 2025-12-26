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

# --- 3. DISEÑO VISUAL (CORRECCIÓN QUIRÚRGICA DE CONTRASTE) ---
st.markdown(f"""
    <style>
    /* Fondo General y Textos Base en Blanco */
    .stApp {{ background-color: #000000; color: #FFFFFF !important; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}
    
    /* TODO EL TEXTO DE LA PÁGINA EN BLANCO (Etiquetas, mensajes, títulos) */
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab, li, h1, h2, h3, .stWarning, .stInfo, .stExpander p {{ 
        color: #FFFFFF !important; 
    }}

    /* FORZAR BLANCO ESPECÍFICO PARA LABELS DE INPUTS (Nombre, Usuario, Buscar producto, etc) */
    div[data-testid="stWidgetLabel"] p {{
        color: #FFFFFF !important;
    }}

    /* --- TEXTO NEGRO ÚNICAMENTE DENTRO DE LOS CAMPOS BLANCOS --- */
    /* 1. Input de búsqueda */
    .stTextInput>div>div>input {{ 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
    }}
    
    /* 2. Caja de Selección (Selectbox) - El valor seleccionado */
    div[data-baseweb="select"] > div {{ 
        background-color: #FFFFFF !important; 
    }}
    div[data-baseweb="select"] div[data-testid="stMarkdownContainer"] p,
    div[data-baseweb="select"] span {{
        color: #000000 !important;
    }}

    /* 3. Lista de opciones del desplegable (Menú cascada) */
    ul[role="listbox"] li, 
    div[role="option"] p,
    div[role="option"] span {{
        color: #000000 !important;
    }}

    /* Notificaciones (Toasts) */
    [data-testid="stToast"] {{ background-color: #FFCC00 !important; border: 1px solid #000000 !important; }}
    [data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{ color: #000000 !important; font-weight: bold !important; }}

    /* Botón Menú iPhone */
    [data-testid="stSidebarCollapsedControl"] {{
        background-color: #FFCC00 !important;
        left: 10px !important;
        top: 10px !important;
        width: 50px !important;
        height: 50px !important;
        z-index: 1000000 !important;
    }}
    [data-testid="stSidebarCollapsedControl"] svg {{ fill: #000000 !important; }}

    /* BOTONES AE: 170.86px x 32.59px */
    div.stButton > button {{
        background-color: #FFCC00 !important;
        color: #000000 !important;
        font-weight: bold !important;
        min-width: 170.86px !important;
        max-width: 170.86px !important;
        height: 32.59px !important;
        border-radius: 4px;
        margin-bottom: -18px !important;
    }}
    div.stButton > button p {{ font-size: 13px !important; color: #000000 !important; }}
    
    .nav-active > div > button {{ background-color: #FFFFFF !important; border: 2px solid #FFCC00 !important; }}
    .red-btn > div > button {{ background-color: #DD0000 !important; }}
    .green-btn > div > button {{ background-color: #28a745 !important; }}
    
    [data-testid="stDataEditor"] div {{ font-size: 11px !important; }}
    .user-info {{ font-family: monospace; white-space: pre; color: #FFCC00; font-size: 12px; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNCIONES LÓGICAS ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

# --- 5. PANTALLAS ---
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario Mensual")
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    
    res = supabase.table("productos_maestro").select("*").execute().data
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
            st.toast(f"✅ Se agregó: {p['nombre']}")

    if st.session_state.carritos[user_key]:
        df = pd.DataFrame(st.session_state.carritos[user_key])
        ed = st.data_editor(df, column_config={"id_producto": None, "Factor": None, "Producto": st.column_config.TextColumn(disabled=True)}, use_container_width=True)
        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("Finalizar"):
                sid = f"SES-{user_key[:3].upper()}-{datetime.now().strftime('%m%d%H%M')}"
                for r in ed.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({
                        "id_local": local_id, "id_producto": r['id_producto'], 
                        "cantidad": r['Cantidad']*r['Factor'], "tipo_movimiento": "CONTEO", 
                        "ubicacion": r['Ubicación'], "notas": sid
                    }).execute()
                st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("Borrar"): st.session_state.carritos[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla():
    st.header("📊 Reportes")
    query = supabase.table("movimientos_inventario").select("*, productos_maestro(nombre, formato_medida)").eq("tipo_movimiento", "CONTEO").execute().data
    if not query:
        st.warning("No hay registros.")
        return
    
    df = pd.json_normalize(query)
    sesiones = sorted(df['notas'].unique().tolist(), reverse=True)
    sesion_sel = st.selectbox("Seleccione Sesión:", sesiones)
    
    if sesion_sel:
        df_s = df[df['notas'] == sesion_sel].copy()
        df_s['factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
        df_s['Unidades'] = (df_s['cantidad'] / df_s['factor']).round(2)
        st.dataframe(df_s[['productos_maestro.nombre', 'ubicacion', 'Unidades', 'productos_maestro.formato_medida']], use_container_width=True)

def admin_maestro():
    st.header("⚙️ Maestro")
    with st.expander("📤 Carga Masiva (Excel / CSV)"):
        up = st.file_uploader("Subir archivo", type=["xlsx", "csv"])
        if up and st.button("Procesar Carga"):
            try:
                df_up = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                supabase.table("productos_maestro").upsert(df_up.to_dict(orient='records')).execute()
                st.success("Carga exitosa"); st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
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
                st.session_state.u_act = None; st.rerun()
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
    sync_session()

    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login"):
                u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Ingresar"):
                    if u.lower() == "admin" and p == "654321.": 
                        st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}
                        st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        st.session_state.auth_user = {"user": u, "role": res[0]['rol'], "local": res[0]['id_local']}
                        st.rerun()
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
    st.sidebar.divider()

    opts = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    for o in opts:
        act = "nav-active" if st.session_state.opt == o else ""
        st.sidebar.markdown(f'<div class="{act}">', unsafe_allow_html=True)
        if st.sidebar.button(o): st.session_state.opt = o; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.divider()
    if st.sidebar.button("Cerrar Sesión"): logout()

    if st.session_state.opt == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": reportes_pantalla()
    elif st.session_state.opt == "👤 Usuarios": admin_usuarios(ld)
    elif st.session_state.opt == "⚙️ Maestro": admin_maestro()

if __name__ == "__main__": main()
