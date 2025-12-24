import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- 1. CONFIGURACIÓN Y CIBERSEGURIDAD ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Error de configuración: Verifica los Secrets.")
    st.stop()

# --- 2. DISEÑO VISUAL "ALEMAN EXPERTO" ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span, .stHeader { color: #FFFFFF !important; }
    
    /* Inputs y Selectores */
    .stSelectbox div[data-baseweb="select"] > div { background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #1A1A1A; color: white; border: 1px solid #333; }
    
    /* BOTÓN LOGIN: Fondo blanco, letras negras */
    div.stButton > button:first-child {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: none !important;
        width: 100%;
    }
    
    /* Botones Rojos para Acciones */
    .red-btn > div > button {
        background-color: #DD0000 !important;
        color: white !important;
    }
    
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO (DATA) ---
def get_locales_map():
    """Obtiene los locales desde la BD (id y nombre)"""
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

# --- 4. LÓGICA DE ACCESO (LOGIN) ---
def login_screen():
    locales_dict = get_locales_map()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("Logo AE.jpg", width=250)
        except:
            st.title("ALEMAN EXPERTO")
            
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            loc_sel = st.selectbox("Local de Acceso", list(locales_dict.keys()) if locales_dict else ["Cargue locales primero"])
            submitted = st.form_submit_button("INGRESAR")
            
            if submitted:
                # Super Admin
                if u.lower() == "admin" and p == "654321.":
                    st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": locales_dict.get(loc_sel, 1)}
                    st.rerun()
                # Usuario de Tabla
                else:
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute()
                    if res.data:
                        st.session_state.auth_user = {
                            "user": res.data[0]['usuario'], 
                            "role": res.data[0]['rol'], 
                            "local": res.data[0]['id_local']
                        }
                        st.rerun()
                    else:
                        st.error("🚫 Usuario no registrado o credenciales inválidas.")

# --- 5. PANTALLAS PRINCIPALES ---

def registro_pantalla(local_id):
    st.header("📥 Registro de Movimiento")
    
    # Buscador de productos coincidente
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("Cargue productos en el Maestro.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Buscar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            peso = st.number_input(f"Cantidad Recibida:", min_value=0.0)
            unid = st.selectbox("Unidad:", ["gramos", "kilos", "litros", "cc"])
        
        # Calculadora de unidades
        mult = 1000 if unid in ["kilos", "litros"] else 1
        total_umb = peso * mult

        st.markdown('<div class="red-btn">', unsafe_allow_html=True)
        if st.button("GUARDAR REGISTRO"):
            valor_inventario = total_umb if tipo == "ENTRADA" else -total_umb
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id, "id_producto": p['id'], "cantidad": valor_inventario, 
                "tipo_movimiento": tipo, "ubicacion": ubi, "peso_verificado": peso, "unidad_peso_verificado": unid
            }).execute()
            st.success(f"✅ {tipo} guardada correctamente.")
        st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla(locales_dict):
    st.header("📊 Reportes de Inventario")
    
    loc_options = ["Todos los Locales"] + list(locales_dict.keys())
    filtro_local = st.selectbox("Filtrar por Local:", loc_options)
    
    # Query de movimientos con Join al maestro
    query = supabase.table("movimientos_inventario").select("cantidad, id_local, productos_maestro(nombre, formato_medida, umb)")
    
    if filtro_local != "Todos los Locales":
        query = query.eq("id_local", locales_dict[filtro_local])
    
    data = query.execute().data
    
    if data:
        df = pd.json_normalize(data)
        # Agrupar para mostrar stock actual (Suma de entradas y salidas)
        df_stock = df.groupby(['productos_maestro.nombre', 'productos_maestro.formato_medida', 'productos_maestro.umb']).agg({'cantidad': 'sum'}).reset_index()
        df_stock.columns = ['Producto', 'Formato', 'Unidad Base', 'Stock Actual']
        st.dataframe(df_stock, use_container_width=True)
    else:
        st.info("No hay registros para mostrar.")

def mantenedor_usuarios(locales_dict):
    st.header("👤 Gestión de Usuarios")
    
    with st.form("UserForm"):
        n = st.text_input("Nombre y Apellido")
        c = st.text_input("Correo")
        l_sel = st.selectbox("Asignar Local", list(locales_dict.keys()))
        u = st.text_input("Usuario (Login)")
        p = st.text_input("Clave", type="password")
        r = st.selectbox("Rol", ["Staff", "Admin"])
        
        if st.form_submit_button("GUARDAR / ACTUALIZAR USUARIO"):
            data = {"nombre_apellido": n, "correo": c, "id_local": locales_dict[l_sel], "usuario": u, "clave": p, "rol": r}
            supabase.table("usuarios_sistema").upsert(data, on_conflict="usuario").execute()
            st.success(f"Usuario {u} procesado.")

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    file = st.file_uploader("Subir Excel Maestro", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        if st.button("ACTUALIZAR MAESTRO"):
            supabase.table("productos_maestro").upsert(df.to_dict(orient='records')).execute()
            st.success("Base de productos actualizada.")

# --- 6. EJECUCIÓN PRINCIPAL ---
def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    locales_dict = get_locales_map()
    locales_inv = {v: k for k, v in locales_dict.items()}
    nombre_local = locales_inv.get(user['local'], "N/A")

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    st.sidebar.markdown(f"**Usuario:** {user['user']} | **Sede:** {nombre_local}")
    
    menu = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin":
        menu.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    
    choice = st.sidebar.radio("Navegación", menu)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    if choice == "📥 Registro Movimiento":
        registro_pantalla(user['local'])
    elif choice == "📊 Reportes":
        reportes_pantalla(locales_dict)
    elif choice == "👤 Mantenedor Usuarios":
        mantenedor_usuarios(locales_dict)
    elif choice == "⚙️ Maestro Productos":
        admin_panel()

if __name__ == "__main__":
    main()
