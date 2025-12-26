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

# --- 2. DISEÑO VISUAL CORREGIDO ---
# Se ajustó el CSS para que el texto sea siempre visible y negro en los botones estándar
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab { color: #FFFFFF !important; }
    
    /* Botones Estándar (Login, Añadir, Guardar) */
    div.stButton > button {
        background-color: #FFCC00 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: 1px solid #FFCC00 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    /* Forzar que el texto del botón se vea siempre negro */
    div.stButton > button p {
        color: #000000 !important;
    }

    /* Botones Especiales */
    .red-btn > div > button { background-color: #DD0000 !important; border-color: #DD0000 !important; }
    .red-btn > div > button p { color: #FFFFFF !important; }
    
    .green-btn > div > button { background-color: #28a745 !important; border-color: #28a745 !important; }
    .green-btn > div > button p { color: #FFFFFF !important; }
    
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
    
    if 'carritos_usuarios' not in st.session_state:
        st.session_state.carritos_usuarios = {}
    
    if user_key not in st.session_state.carritos_usuarios:
        st.session_state.carritos_usuarios[user_key] = []

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    
    busqueda = st.text_input("🔍 Buscar producto para contar:", placeholder="Escribe el nombre...")
    opciones = [opc for opc in prod_map.keys() if busqueda.lower() in opc.lower()]
    seleccion = st.selectbox("Selecciona producto:", [""] + opciones)
    
    if seleccion:
        p = prod_map[seleccion]
        factor = extraer_valor_formato(p['formato_medida'])
        
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
        with col2:
            cant = st.number_input(f"Cantidad ({p['formato_medida']}):", min_value=0.0, step=1.0)
        
        if st.button("AÑADIR AL CONTEO"):
            item = {
                "id_producto": p['id'],
                "Producto": p['nombre'],
                "Ubicación": ubi,
                "Cantidad": float(cant),
                "Formato": p['formato_medida'],
                "Factor": factor
            }
            st.session_state.carritos_usuarios[user_key].append(item)
            st.toast(f"Añadido: {p['nombre']}")

    if st.session_state.carritos_usuarios[user_key]:
        st.divider()
        st.subheader("📝 Estado de inventario actual")
        df_temp = pd.DataFrame(st.session_state.carritos_usuarios[user_key])
        
        edited_df = st.data_editor(
            df_temp,
            column_config={
                "id_producto": None, "Factor": None,
                "Producto": st.column_config.TextColumn(disabled=True),
                "Formato": st.column_config.TextColumn(disabled=True),
                "Ubicación": st.column_config.SelectboxColumn(options=["Bodega", "Cámara de frío", "Producción", "Cocina"], required=True),
                "Cantidad": st.column_config.NumberColumn(min_value=0, step=1)
            },
            num_rows="dynamic", use_container_width=True, key=f"editor_{user_key}"
        )

        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("✅ FINALIZAR Y CARGAR"):
                session_id = f"SES-{user_key[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M')}"
                for row in edited_df.to_dict(orient='records'):
                    total_umb = row['Cantidad'] * row['Factor']
                    supabase.table("movimientos_inventario").insert({
                        "id_local": local_id, "id_producto": row['id_producto'], "cantidad": total_umb,
                        "tipo_movimiento": "CONTEO", "ubicacion": row['Ubicación'], "notas": session_id
                    }).execute()
                st.session_state.carritos_usuarios[user_key] = []
                st.success(f"Inventario cargado: {session_id}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_cancel:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("🗑️ CANCELAR SESIÓN"):
                st.session_state.carritos_usuarios[user_key] = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla(locales_dict):
    st.header("📊 Reportes por Sesión")
    query = supabase.table("movimientos_inventario").select("*, productos_maestro(nombre, formato_medida, umb)").eq("tipo_movimiento", "CONTEO")
    data = query.execute().data
    if not data:
        st.warning("No hay registros de inventario.")
        return
    df = pd.json_normalize(data)
    if 'notas' in df.columns:
        sesiones = sorted(df['notas'].unique().tolist(), reverse=True)
        sesion_select = st.selectbox("Seleccione Sesión:", sesiones)
        if sesion_select:
            df_sesion = df[df['notas'] == sesion_select].copy()
            df_sesion['factor'] = df_sesion['productos_maestro.formato_medida'].apply(extraer_valor_formato)
            df_sesion['Cant_Ing'] = (df_sesion['cantidad'] / df_sesion['factor']).round(2)
            detalle = df_sesion[['productos_maestro.nombre', 'ubicacion', 'Cant_Ing', 'productos_maestro.formato_medida']]
            detalle.columns = ['Producto', 'Ubicación', 'Cantidad', 'Formato']
            st.dataframe(detalle, use_container_width=True)

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    
    with st.expander("📤 Carga Masiva desde Excel/CSV"):
        uploaded_file = st.file_uploader("Elegir archivo", type=["xlsx", "csv"])
        if uploaded_file:
            try:
                df_upload = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                st.dataframe(df_upload.head())
                if st.button("🚀 INICIAR CARGA MASIVA"):
                    supabase.table("productos_maestro").upsert(df_upload.to_dict(orient='records')).execute()
                    st.success("¡Carga masiva completada!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.subheader("✏️ Editor de Productos")
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        df_prod = pd.DataFrame(res)
        edited_df = st.data_editor(df_prod, num_rows="dynamic", use_container_width=True, key="maestro_editor")
        if st.button("💾 GUARDAR CAMBIOS"):
            supabase.table("productos_maestro").upsert(edited_df.to_dict(orient='records')).execute()
            st.success("¡Cambios guardados!")
            st.rerun()

def main():
    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=250)
            with st.form("Login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("INGRESAR"):
                    if u.lower() == "admin" and p == "654321.":
                        st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}
                        st.rerun()
                    else:
                        res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute()
                        if res.data:
                            st.session_state.auth_user = {"user": u, "role": res.data[0]['rol'], "local": res.data[0]['id_local']}
                            st.rerun()
                        else: st.error("Credenciales incorrectas.")
        return

    user = st.session_state.auth_user
    locales_dict = get_locales_map()
    locales_inv = {v: k for k, v in locales_dict.items()}

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        current_name = locales_inv.get(user['local'], list(locales_dict.keys())[0])
        nuevo_local = st.sidebar.selectbox("Cambio de Sede:", list(locales_dict.keys()), index=list(locales_dict.keys()).index(current_name))
        user['local'] = locales_dict[nuevo_local]

    st.sidebar.markdown(f"**Usuario:** {user['user']} | **Sede:** {locales_inv.get(user['local'])}")
    menu = ["📋 Ingreso de Inventario", "📊 Reportes", "👤 Mantenedor Usuarios", "⚙️ Maestro Productos"]
    choice = st.sidebar.radio("Navegación", menu if user['role'] == "Admin" else menu[:2])

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    if choice == "📋 Ingreso de Inventario": ingreso_inventario_pantalla(user['local'], user['user'])
    elif choice == "📊 Reportes": reportes_pantalla(locales_dict)
    elif choice == "👤 Mantenedor Usuarios": mantenedor_usuarios(locales_dict)
    elif choice == "⚙️ Maestro Productos": admin_panel()

if __name__ == "__main__":
    main()
