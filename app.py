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

# --- 2. DISEÑO VISUAL PERFECCIONADO ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab { color: #FFFFFF !important; }
    
    /* BOTONES GLOBALES: Uniformes y con espaciado reducido */
    div.stButton > button {
        background-color: #FFCC00 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 1px solid #FFCC00 !important;
        width: 100% !important; /* Largo uniforme */
        margin-bottom: -10px !important; /* Reduce espacio entre botones */
        border-radius: 5px;
        padding: 0.4rem;
    }
    
    div.stButton > button p { color: #000000 !important; font-size: 15px; }

    /* Estilo para el botón activo en navegación */
    .nav-active > div > button {
        background-color: #FFFFFF !important;
        border: 2px solid #FFCC00 !important;
    }

    /* Botones de acción crítica */
    .red-btn > div > button { background-color: #DD0000 !important; border-color: #DD0000 !important; }
    .red-btn > div > button p { color: #FFFFFF !important; }
    .green-btn > div > button { background-color: #28a745 !important; border-color: #28a745 !important; }
    .green-btn > div > button p { color: #FFFFFF !important; }

    /* Inputs y Selectores */
    .stSelectbox div[data-baseweb="select"] > div { background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #1A1A1A; color: white; border: 1px solid #333; }
    
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

# --- 4. PANTALLAS ---

def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario Mensual")
    if 'carritos_usuarios' not in st.session_state: st.session_state.carritos_usuarios = {}
    if user_key not in st.session_state.carritos_usuarios: st.session_state.carritos_usuarios[user_key] = []

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    
    busqueda = st.text_input("🔍 Buscar producto:", placeholder="Escribe el nombre...")
    opciones = [opc for opc in prod_map.keys() if busqueda.lower() in opc.lower()]
    seleccion = st.selectbox("Selecciona producto:", [""] + opciones)
    
    if seleccion:
        p = prod_map[seleccion]
        col1, col2 = st.columns(2)
        with col1: ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
        with col2: cant = st.number_input(f"Cantidad ({p['formato_medida']}):", min_value=0.0, step=1.0)
        
        if st.button("Ingresar a inventario"):
            item = {"id_producto": p['id'], "Producto": p['nombre'], "Ubicación": ubi, "Cantidad": float(cant), "Formato": p['formato_medida'], "Factor": extraer_valor_formato(p['formato_medida'])}
            st.session_state.carritos_usuarios[user_key].append(item)
            st.toast(f"Añadido: {p['nombre']}")

    if st.session_state.carritos_usuarios[user_key]:
        st.divider()
        st.subheader("📝 Estado de inventario actual")
        df_temp = pd.DataFrame(st.session_state.carritos_usuarios[user_key])
        edited_df = st.data_editor(df_temp, column_config={"id_producto": None, "Factor": None, "Producto": st.column_config.TextColumn(disabled=True), "Formato": st.column_config.TextColumn(disabled=True), "Ubicación": st.column_config.SelectboxColumn(options=["Bodega", "Cámara de frío", "Producción", "Cocina"], required=True), "Cantidad": st.column_config.NumberColumn(min_value=0, step=1)}, num_rows="dynamic", use_container_width=True, key=f"editor_{user_key}")

        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("✅ FINALIZAR Y CARGAR"):
                sid = f"SES-{user_key[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M')}"
                for r in edited_df.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({"id_local": local_id, "id_producto": r['id_producto'], "cantidad": r['Cantidad']*r['Factor'], "tipo_movimiento": "CONTEO", "ubicacion": r['Ubicación'], "notas": sid}).execute()
                st.session_state.carritos_usuarios[user_key] = []; st.success(f"Cargado: {sid}"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("🗑️ CANCELAR SESIÓN"): st.session_state.carritos_usuarios[user_key] = []; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla():
    st.header("📊 Reportes por Sesión")
    query = supabase.table("movimientos_inventario").select("*, productos_maestro(nombre, formato_medida)").eq("tipo_movimiento", "CONTEO").execute().data
    if not query: st.warning("Sin registros."); return
    df = pd.json_normalize(query)
    sesiones = sorted(df['notas'].unique().tolist(), reverse=True)
    s_sel = st.selectbox("Seleccione Sesión:", sesiones)
    if s_sel:
        df_s = df[df['notas'] == s_sel].copy()
        df_s['factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
        df_s['Cant'] = (df_s['cantidad'] / df_s['factor']).round(2)
        st.dataframe(df_s[['productos_maestro.nombre', 'ubicacion', 'Cant', 'productos_maestro.formato_medida']], use_container_width=True)

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    with st.expander("📤 Carga Masiva"):
        up = st.file_uploader("Subir Excel/CSV", type=["xlsx", "csv"])
        if up and st.button("🚀 Iniciar carga masiva"):
            df = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
            supabase.table("productos_maestro").upsert(df.to_dict(orient='records')).execute()
            st.success("Carga lista."); st.rerun()
    st.divider()
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        ed = st.data_editor(pd.DataFrame(res), num_rows="dynamic", use_container_width=True, key="m_edit")
        if st.button("💾 Guardar cambios"): supabase.table("productos_maestro").upsert(ed.to_dict(orient='records')).execute(); st.success("Guardado."); st.rerun()

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
                    else: st.error("Error de acceso.")
        return

    if 'menu_option' not in st.session_state: st.session_state.menu_option = "📋 Ingreso de Inventario"
    user = st.session_state.auth_user
    ld = get_locales_map(); li = {v: k for k, v in ld.items()}

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        curr = li.get(user['local'], list(ld.keys())[0])
        new_l = st.sidebar.selectbox("Cambio de Sede:", list(ld.keys()), index=list(ld.keys()).index(curr))
        user['local'] = ld[new_l]

    st.sidebar.markdown(f"**Usuario:** {user['user']}  \n**Sede:** {li.get(user['local'])}")
    st.sidebar.divider()

    opciones = ["📋 Ingreso de Inventario", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso de Inventario", "📊 Reportes"]
    for opt in opciones:
        is_active = "nav-active" if st.session_state.menu_option == opt else ""
        st.sidebar.markdown(f'<div class="{is_active}">', unsafe_allow_html=True)
        if st.sidebar.button(opt): st.session_state.menu_option = opt; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.divider()
    if st.sidebar.button("Cerrar Sesión"): del st.session_state.auth_user; st.rerun()

    if st.session_state.menu_option == "📋 Ingreso de Inventario": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.menu_option == "📊 Reportes": reportes_pantalla()
    elif st.session_state.menu_option == "👤 Usuarios":
        st.header("👤 Gestión de Usuarios")
        with st.form("UForm"):
            n = st.text_input("Nombre"); u = st.text_input("Usuario"); p = st.text_input("Clave"); r = st.selectbox("Rol", ["Staff", "Admin"])
            if st.form_submit_button("Guardar"):
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": user['local'], "usuario": u, "clave": p, "rol": r}, on_conflict="usuario").execute()
                st.success("Guardado.")
    elif st.session_state.menu_option == "⚙️ Maestro": admin_panel()

if __name__ == "__main__": main()
