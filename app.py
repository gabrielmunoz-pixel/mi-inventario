import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURACIÓN DE CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Configura los Secrets en Streamlit.")
    st.stop()

# --- DISEÑO VISUAL "ALEMAN EXPERTO" (FONDO NEGRO / TEXTO BLANCO) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; }
    .stMarkdown, p, label { color: #FFFFFF !important; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #222222; color: white; }
    .stButton>button { background-color: #DD0000; color: white; border: none; }
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    
    # Menú de Navegación
    options = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == 'Admin':
        options.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    
    choice = st.sidebar.radio("Menú", options)

    if choice == "📥 Registro Movimiento":
        registro_pantalla(user['local'])
    elif choice == "👤 Mantenedor Usuarios":
        mantenedor_usuarios()
    elif choice == "⚙️ Maestro Productos":
        admin_panel()

def login_screen():
    st.image("Logo AE.jpg", width=200)
    with st.form("Login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("INGRESAR"):
            # Lógica simple: si es 'admin' entra como tal
            role = 'Admin' if u.lower() == 'admin' else 'Staff'
            st.session_state.auth_user = {"user": u, "role": role, "local": 1}
            st.rerun()

def registro_pantalla(local_id):
    st.header("📥 Ingreso de Inventario")
    
    # 1. BÚSQUEDA Y SELECCIÓN INTEGRADA
    res = supabase.table("productos_maestro").select("*").execute().data
    prod_map = {f"{p['nombre']} ({p['formato_medida']})": p for p in res}
    
    seleccion = st.selectbox("Buscar y Seleccionar Producto:", [""] + list(prod_map.keys()), help="Escribe para filtrar")
    
    if seleccion:
        p = prod_map[seleccion]
        st.markdown(f"**Unidad Base:** {p['umb']} | **Factor:** {p['factor_conversion']}")
        
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                ubicacion = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
                tipo_mov = st.radio("Operación:", ["ENTRADA", "SALIDA"])
            
            with col2:
                peso_val = st.number_input("Peso/Cantidad recibida:", min_value=0.0)
                unidad_peso = st.selectbox("Unidad:", ["gramos", "kilos", "litros", "cc"])
        
        # CALCULADORA AUTOMÁTICA
        # Convertimos todo a la UMB del producto para el stock
        multiplicador = 1000 if unidad_peso in ["kilos", "litros"] else 1
        total_umb = peso_val * multiplicador

        if st.button("CONFIRMAR REGISTRO"):
            ajuste = total_umb if tipo_mov == "ENTRADA" else -total_umb
            # Guardar movimiento con los nuevos campos
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id, 
                "id_producto": p['id'], 
                "cantidad": total_umb, 
                "tipo_movimiento": tipo_mov,
                "ubicacion": ubicacion,
                "peso_verificado": peso_val,
                "unidad_peso_verificado": unidad_peso
            }).execute()
            st.success(f"✅ Registrado: {total_umb} {p['umb']} en {ubicacion}")

def mantenedor_usuarios():
    st.header("👤 Gestión de Usuarios")
    
    tab1, tab2 = st.tabs(["Crear Usuario", "Usuarios Activos"])
    
    with tab1:
        with st.form("new_user"):
            new_u = st.text_input("Nombre de Usuario")
            new_r = st.selectbox("Rol", ["Staff", "Admin"])
            new_l = st.number_input("Local Asignado", min_value=1, value=1)
            if st.form_submit_button("Guardar Usuario"):
                # Aquí podrías usar la tabla 'auth' de Supabase o una tabla propia
                st.success(f"Usuario {new_u} creado (Simulado - Conecta con Supabase Auth si deseas real)")

    with tab2:
        st.write("Lista de accesos registrados:")
        # Ejemplo de visualización
        st.table([{"ID": 1, "User": "admin", "Rol": "Admin"}, {"ID": 2, "User": "cocina1", "Rol": "Staff"}])

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    file = st.file_uploader("Subir Excel", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        if st.button("Cargar Datos"):
            supabase.table("productos_maestro").upsert(df.to_dict(orient='records')).execute()
            st.success("Maestro actualizado.")

if __name__ == "__main__":
    main()
