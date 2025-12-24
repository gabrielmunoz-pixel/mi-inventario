import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- 2. DISEÑO VISUAL (CORRECCIÓN AGRESIVA DE BOTONES) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab { color: #FFFFFF !important; }
    
    /* CORRECCIÓN BOTÓN BLANCO: Forzar texto negro visible */
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: 2px solid #FFCC00 !important;
        opacity: 1 !important;
    }
    
    /* Selectbox e Inputs */
    .stSelectbox div[data-baseweb="select"] > div { background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #1A1A1A; color: white; border: 1px solid #333; }

    /* BOTONES ROJOS (Borrar/Confirmar) */
    .red-btn > div > button {
        background-color: #DD0000 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def get_stock_actual(producto_id, local_id):
    res = supabase.table("movimientos_inventario").select("cantidad").eq("id_producto", producto_id).eq("id_local", local_id).execute().data
    return sum(item['cantidad'] for item in res) if res else 0

# --- 4. PANTALLAS ---

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try: st.image("Logo AE.jpg", width=250)
        except: st.title("ALEMAN EXPERTO")
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
                    else:
                        st.error("🚫 Credenciales incorrectas.")

def registro_pantalla(local_id):
    st.header("📥 Registro de Movimiento")
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Buscar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        stock_disp = get_stock_actual(p['id'], local_id)
        st.info(f"Existencia actual: {stock_disp} {p['umb']}")
        
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            peso = st.number_input("Cantidad:", min_value=0.0)
            unid = st.selectbox("Unidad:", ["gramos", "cc", "Unitario", "kilos", "litros"])
        
        mult = 1000 if unid in ["kilos", "litros"] else 1
        total_umb = peso * mult

        st.markdown('<div class="red-btn">', unsafe_allow_html=True)
        if st.button("CONFIRMAR MOVIMIENTO"):
            if tipo == "SALIDA" and total_umb > stock_disp:
                st.error("❌ Stock Insuficiente.")
            else:
                valor = total_umb if tipo == "ENTRADA" else -total_umb
                supabase.table("movimientos_inventario").insert({
                    "id_local": local_id, "id_producto": p['id'], "cantidad": valor, "tipo_movimiento": tipo, "ubicacion": ubi
                }).execute()
                st.success("✅ Actualizado.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def mantenedor_usuarios(locales_dict):
    st.header("👤 Gestión de Usuarios")
    t1, t2 = st.tabs(["Crear / Editar", "Borrar Usuario"])
    
    with t1:
        with st.form("UserForm"):
            n = st.text_input("Nombre y Apellido")
            l_sel = st.selectbox("Local Asignado", list(locales_dict.keys()))
            u = st.text_input("Usuario (Login)")
            p = st.text_input("Clave")
            r = st.selectbox("Rol", ["Staff", "Admin"])
            if st.form_submit_button("GUARDAR / ACTUALIZAR"):
                data = {"nombre_apellido": n, "id_local": locales_dict[l_sel], "usuario": u, "clave": p, "rol": r}
                supabase.table("usuarios_sistema").upsert(data, on_conflict="usuario").execute()
                st.success(f"Usuario {u} procesado.")

    with t2:
        res = supabase.table("usuarios_sistema").select("*").execute().data
        if res:
            df = pd.DataFrame(res)
            st.dataframe(df[["nombre_apellido", "usuario", "rol"]], use_container_width=True)
            user_to_del = st.selectbox("Seleccione usuario para eliminar:", df["usuario"])
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("ELIMINAR DEFINITIVAMENTE"):
                supabase.table("usuarios_sistema").delete().eq("usuario", user_to_del).execute()
                st.warning(f"Usuario {user_to_del} borrado.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    
    # 1. Carga Masiva
    with st.expander("📥 Carga Masiva (Excel)"):
        file = st.file_uploader("Subir .xlsx", type=["xlsx"])
        if file and st.button("PROCESAR EXCEL"):
            df = pd.read_excel(file)
            supabase.table("productos_maestro").upsert(df.to_dict(orient='records')).execute()
            st.success("Maestro actualizado.")

    # 2. Edición Directa
    st.subheader("📝 Edición Rápida de Productos")
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        df_prod = pd.DataFrame(res)
        # st.data_editor permite editar celdas directamente
        edited_df = st.data_editor(df_prod, num_rows="dynamic", key="prod_editor", use_container_width=True)
        
        if st.button("GUARDAR CAMBIOS EN TABLA"):
            # Identificar filas cambiadas y actualizar
            supabase.table("productos_maestro").upsert(edited_df.to_dict(orient='records')).execute()
            st.success("Cambios guardados en la base de datos.")

def reportes_pantalla(locales_dict):
    st.header("📊 Stock por Local")
    filtro = st.selectbox("Sede:", ["Todos"] + list(locales_dict.keys()))
    query = supabase.table("movimientos_inventario").select("cantidad, id_local, productos_maestro(nombre, formato_medida, umb)")
    if filtro != "Todos": query = query.eq("id_local", locales_dict[filtro])
    
    data = query.execute().data
    if data:
        df = pd.json_normalize(data)
        df_stock = df.groupby(['productos_maestro.nombre', 'productos_maestro.formato_medida', 'productos_maestro.umb']).agg({'cantidad': 'sum'}).reset_index()
        df_stock.columns = ['Producto', 'Formato', 'UMB', 'Stock']
        st.dataframe(df_stock, use_container_width=True)

# --- 5. MAIN ---
def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    locales_dict = get_locales_map()
    locales_inv = {v: k for k, v in locales_dict.items()}

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        st.sidebar.subheader("🛠️ Administrador")
        current_name = locales_inv.get(user['local'], list(locales_dict.keys())[0])
        nuevo_local = st.sidebar.selectbox("Local Activo:", list(locales_dict.keys()), index=list(locales_dict.keys()).index(current_name))
        user['local'] = locales_dict[nuevo_local]

    st.sidebar.markdown(f"**Usuario:** {user['user']}")
    st.sidebar.markdown(f"**Sede:** {locales_inv.get(user['local'])}")
    
    menu = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin": menu.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    choice = st.sidebar.radio("Menú", menu)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    if choice == "📥 Registro Movimiento": registro_pantalla(user['local'])
    elif choice == "📊 Reportes": reportes_pantalla(locales_dict)
    elif choice == "👤 Mantenedor Usuarios": mantenedor_usuarios(locales_dict)
    elif choice == "⚙️ Maestro Productos": admin_panel()

if __name__ == "__main__":
    main()
