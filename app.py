import streamlit as st
import pandas as pd
import re
from datetime import datetime
from supabase import create_client, Client

# --- 1. CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- 2. DISEÑO VISUAL ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; color: #FFFFFF; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab {{ color: #FFFFFF !important; }}
    
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
    
    div.stButton > button p {{ color: #000000 !important; font-size: 14px !important; margin: 0 !important; }}
    [data-testid="stVerticalBlock"] > div:has(button) {{ gap: 0.5rem !important; }}

    .nav-active > div > button {{ background-color: #FFFFFF !important; border: 2px solid #FFCC00 !important; }}
    .red-btn > div > button {{ background-color: #DD0000 !important; border-color: #DD0000 !important; }}
    .red-btn > div > button p {{ color: #FFFFFF !important; }}
    .green-btn > div > button {{ background-color: #28a745 !important; border-color: #28a745 !important; }}
    .green-btn > div > button p {{ color: #FFFFFF !important; }}

    .stSelectbox div[data-baseweb="select"] > div {{ background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }}
    .stTextInput>div>div>input {{ background-color: #1A1A1A; color: white; border: 1px solid #333; }}
    h1, h2, h3 {{ color: #FFCC00 !important; }}
    
    .user-info {{ font-family: monospace; white-space: pre; color: #FFCC00; font-size: 13px; margin-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA AUXILIAR ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

# --- 4. PANTALLAS ---

def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario")
    if 'carritos_usuarios' not in st.session_state: st.session_state.carritos_usuarios = {}
    if user_key not in st.session_state.carritos_usuarios: st.session_state.carritos_usuarios[user_key] = []
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    busqueda = st.text_input("🔍 Buscar:", placeholder="Producto...")
    opciones = [opc for opc in prod_map.keys() if busqueda.lower() in opc.lower()]
    seleccion = st.selectbox("Producto:", [""] + opciones)
    if seleccion:
        p = prod_map[seleccion]
        col1, col2 = st.columns(2)
        with col1: ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
        with col2: cant = st.number_input(f"Cant:", min_value=0.0, step=1.0)
        if st.button("Ingresar"):
            item = {"id_producto": p['id'], "Producto": p['nombre'], "Ubicación": ubi, "Cantidad": float(cant), "Formato": p['formato_medida'], "Factor": extraer_valor_formato(p['formato_medida'])}
            st.session_state.carritos_usuarios[user_key].append(item)
            st.toast(f"Ok: {p['nombre']}")
    if st.session_state.carritos_usuarios[user_key]:
        df_temp = pd.DataFrame(st.session_state.carritos_usuarios[user_key])
        edited_df = st.data_editor(df_temp, column_config={"id_producto": None, "Factor": None, "Producto": st.column_config.TextColumn(disabled=True)}, num_rows="dynamic", use_container_width=True)
        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("Finalizar"):
                sid = f"SES-{user_key[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M')}"
                for r in edited_df.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({"id_local": local_id, "id_producto": r['id_producto'], "cantidad": r['Cantidad']*r['Factor'], "tipo_movimiento": "CONTEO", "ubicacion": r['Ubicación'], "notas": sid}).execute()
                st.session_state.carritos_usuarios[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("Cancelar"): st.session_state.carritos_usuarios[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla():
    st.header("📊 Reportes")
    query = supabase.table("movimientos_inventario").select("*, productos_maestro(nombre, formato_medida)").eq("tipo_movimiento", "CONTEO").execute().data
    if not query: st.warning("Sin datos."); return
    df = pd.json_normalize(query)
    sesion = st.selectbox("Sesión:", sorted(df['notas'].unique().tolist(), reverse=True))
    if sesion:
        df_s = df[df['notas'] == sesion].copy()
        df_s['factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
        df_s['Cant'] = (df_s['cantidad'] / df_s['factor']).round(2)
        st.dataframe(df_s[['productos_maestro.nombre', 'ubicacion', 'Cant']], use_container_width=True)

def admin_usuarios(locales_dict):
    st.header("👤 Gestión de Usuarios")
    if 'user_action' not in st.session_state: st.session_state.user_action = None

    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("Crear Admin"): st.session_state.user_action = "admin"
    with c2: 
        if st.button("Crear Staff"): st.session_state.user_action = "staff"
    with c3: 
        if st.button("Modificar/Eliminar"): st.session_state.user_action = "edit"

    st.divider()

    if st.session_state.user_action in ["admin", "staff"]:
        rol_txt = "Administrador" if st.session_state.user_action == "admin" else "Staff"
        st.subheader(f"Nuevo {rol_txt}")
        with st.form("UserForm"):
            n = st.text_input("Nombre Completo")
            u = st.text_input("Nombre de Usuario")
            p = st.text_input("Contraseña")
            l_id = 1
            if st.session_state.user_action == "staff":
                l_sel = st.selectbox("Asignar Sede", list(locales_dict.keys()))
                l_id = locales_dict[l_sel]
            if st.form_submit_button("Guardar"):
                rol_db = "Admin" if st.session_state.user_action == "admin" else "Staff"
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": l_id, "usuario": u, "clave": p, "rol": rol_db}, on_conflict="usuario").execute()
                st.success("Guardado exitosamente."); st.session_state.user_action = None; st.rerun()

    elif st.session_state.user_action == "edit":
        st.subheader("Modificar o Eliminar")
        res = supabase.table("usuarios_sistema").select("*").execute().data
        if res:
            u_map = {x['usuario']: x for x in res}
            u_sel = st.selectbox("Seleccione Usuario", list(u_map.keys()))
            if u_sel:
                curr = u_map[u_sel]
                with st.form("EditForm"):
                    en = st.text_input("Nombre", value=curr['nombre_apellido'])
                    ep = st.text_input("Nueva Clave", value=curr['clave'])
                    col_del, col_save = st.columns(2)
                    if st.form_submit_button("Actualizar Datos"):
                        supabase.table("usuarios_sistema").update({"nombre_apellido": en, "clave": ep}).eq("usuario", u_sel).execute()
                        st.success("Actualizado."); st.rerun()
                st.markdown('<div class="red-btn">', unsafe_allow_html=True)
                if st.button("Eliminar permanentemente"):
                    supabase.table("usuarios_sistema").delete().eq("usuario", u_sel).execute()
                    st.warning("Usuario eliminado."); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

def admin_maestro():
    st.header("⚙️ Maestro")
    with st.expander("📤 Carga Masiva"):
        up = st.file_uploader("Archivo", type=["xlsx", "csv"])
        if up and st.button("Cargar Masivo"):
            df = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
            supabase.table("productos_maestro").upsert(df.to_dict(orient='records')).execute()
            st.success("Cargado."); st.rerun()
    st.divider()
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        ed = st.data_editor(pd.DataFrame(res), num_rows="dynamic", use_container_width=True)
        if st.button("Guardar"): supabase.table("productos_maestro").upsert(ed.to_dict(orient='records')).execute(); st.rerun()

# --- 5. MAIN ---
def main():
    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=250)
            with st.form("Login"):
                u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Ingresar"):
                    if u.lower() == "admin" and p == "654321.": st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}; st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res: st.session_state.auth_user = {"user": u, "role": res[0]['rol'], "local": res[0]['id_local']}; st.rerun()
                    else: st.error("Acceso denegado.")
        return

    if 'menu_option' not in st.session_state: st.session_state.menu_option = "📋 Ingreso"
    user = st.session_state.auth_user
    ld = get_locales_map(); li = {v: k for k, v in ld.items()}

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        user['local'] = ld[st.sidebar.selectbox("Sede:", list(ld.keys()), index=list(ld.keys()).index(li.get(user['local'], list(ld.keys())[0])))]

    st.sidebar.markdown(f"""<div class="user-info">Usuario : {user['user']}\nSede    : {li.get(user['local'], "N/A")}</div>""", unsafe_allow_html=True)
    st.sidebar.divider()

    opts = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    for opt in opts:
        is_active = "nav-active" if st.session_state.menu_option == opt else ""
        st.sidebar.markdown(f'<div class="{is_active}">', unsafe_allow_html=True)
        if st.sidebar.button(opt): st.session_state.menu_option = opt; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.divider()
    if st.sidebar.button("Cerrar Sesión"): del st.session_state.auth_user; st.rerun()

    if st.session_state.menu_option == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.menu_option == "📊 Reportes": reportes_pantalla()
    elif st.session_state.menu_option == "👤 Usuarios": admin_usuarios(ld)
    elif st.session_state.menu_option == "⚙️ Maestro": admin_maestro()

if __name__ == "__main__": main()
