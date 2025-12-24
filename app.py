import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURACIÓN DE CONEXIÓN (CIBERSEGURIDAD) ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Configura SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit.")
    st.stop()

# --- DISEÑO VISUAL "ALEMAN EXPERTO" (FONDO NEGRO / TEXTO BLANCO) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; }
    .stMarkdown, p, label, .stMetric { color: #FFFFFF !important; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #222222; color: white; border: 1px solid #FFCC00; }
    .stButton>button { background-color: #DD0000; color: white; border-radius: 5px; width: 100%; font-weight: bold; }
    h1, h2, h3 { color: #FFCC00 !important; }
    /* Ajuste para que las tablas se vean bien en fondo negro */
    .stDataFrame { border: 1px solid #333333; }
    </style>
    """, unsafe_allow_html=True)

def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    
    # BARRA LATERAL
    try:
        st.sidebar.image("Logo AE.jpg", use_container_width=True)
    except:
        st.sidebar.title("🇩🇪 AE")
        
    st.sidebar.markdown(f"**Usuario:** {user['user']}")
    st.sidebar.markdown(f"**Rol:** {user['role']}")
    
    # DEFINICIÓN DE MENÚ SEGÚN ROL
    options = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == 'Admin':
        options.append("👤 Mantenedor Usuarios")
        options.append("⚙️ Maestro Productos")
    
    choice = st.sidebar.radio("Navegación Principal", options)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    # ENRUTAMIENTO DE PÁGINAS
    if choice == "📥 Registro Movimiento":
        registro_pantalla(user['local'])
    elif choice == "📊 Reportes":
        reportes_pantalla()
    elif choice == "👤 Mantenedor Usuarios":
        mantenedor_usuarios()
    elif choice == "⚙️ Maestro Productos":
        admin_panel()

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("Logo AE.jpg", width=250)
        except:
            st.header("ALEMAN EXPERTO")
            
        with st.form("Login Form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("INGRESAR")
            
            if submitted:
                # VALIDACIÓN DEL USUARIO ADMINISTRADOR DEFINIDO
                if u == "Admin" and p == "654321.":
                    st.session_state.auth_user = {"user": u, "role": "Admin", "local": 1}
                    st.success("Acceso Administrador concedido")
                    st.rerun()
                # Aquí podrías agregar validación para usuarios Staff desde la base de datos
                elif u != "" and p != "":
                    st.session_state.auth_user = {"user": u, "role": "Staff", "local": 1}
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

def registro_pantalla(local_id):
    st.header("📥 Registro de Movimientos")
    
    # 1. Búsqueda y Selección Integrada (Funciona como menú desplegable que filtra)
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("No hay productos en el maestro. Cárgalos en la sección de Administrador.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Buscar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            ubicacion = st.selectbox("Ubicación Física:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo_mov = st.radio("Operación:", ["ENTRADA", "SALIDA"])
            
        with col2:
            peso_val = st.number_input(f"Peso/Cantidad ({p['umb']}):", min_value=0.0)
            unidad_peso = st.selectbox("Unidad de ingreso:", ["gramos", "kilos", "litros", "cc"])
        
        # LÓGICA DE CONVERSIÓN A UNIDAD BASE (UMB)
        # Si el usuario ingresa kilos o litros, multiplicamos por 1000 para llevar a gramos o cc
        factor_unitario = 1000 if unidad_peso in ["kilos", "litros"] else 1
        total_umb = peso_val * factor_unitario

        if st.button("CONFIRMAR Y GUARDAR"):
            ajuste = total_umb if tipo_mov == "ENTRADA" else -total_umb
            
            # Registro en Movimientos (Auditoría)
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id,
                "id_producto": p['id'],
                "cantidad": total_umb,
                "tipo_movimiento": tipo_mov,
                "ubicacion": ubicacion,
                "peso_verificado": peso_val,
                "unidad_peso_verificado": unidad_peso
            }).execute()
            
            # Actualización de Stock Consolidado
            # (Aquí iría la lógica de actualización de la tabla stock_config)
            
            st.balloons()
            st.success(f"Movimiento registrado: {total_umb} {p['umb']} en {ubicacion}")

def reportes_pantalla():
    st.header("📊 Reportes de Inventario")
    st.write("Vista de stock actual por local y ubicación.")
    # Implementar query de stock_config aquí

def mantenedor_usuarios():
    st.header("👤 Gestión de Usuarios (Admin)")
    # Aquí es donde podrás crear y eliminar usuarios en las próximas versiones
    st.info("Funcionalidad de mantenedor en desarrollo. Aquí aparecerá la lista de usuarios de Supabase Auth.")

def admin_panel():
    st.header("⚙️ Maestro de Productos (Admin)")
    st.markdown("Carga masiva de productos mediante archivo Excel.")
    file = st.file_uploader("Subir archivo Excel .xlsx", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        st.dataframe(df.head())
        if st.button("Procesar Carga Masiva"):
            # El script original se define como el "original"
            data = df.to_dict(orient='records')
            supabase.table("productos_maestro").upsert(data).execute()
            st.success("Maestro actualizado correctamente.")

if __name__ == "__main__":
    main()
