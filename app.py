import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONEXIÓN Y CIBERSEGURIDAD ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- ESTILO VISUAL NEGRO Y BLANCO ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span { color: #FFFFFF !important; }
    .stSelectbox div[data-baseweb="select"] > div { background-color: #222222; color: white; border: 1px solid #FFCC00; }
    .stButton>button { background-color: #DD0000; color: white; border-radius: 5px; width: 100%; font-weight: bold; }
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

def main():
    # Inicialización de sesión si no existe
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    
    # BARRA LATERAL CON LOGO
    try:
        st.sidebar.image("Logo AE.jpg", use_container_width=True)
    except:
        st.sidebar.title("🇩🇪 ALEMAN EXPERTO")
        
    st.sidebar.markdown(f"**Usuario:** {user['user']}")
    st.sidebar.markdown(f"**Nivel de Acceso:** {user['role']}")
    
    # --- LÓGICA DE MENÚ ESTRICTA ---
    # Si el rol es 'Admin', mostramos todas las opciones
    options = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin":
        options.append("👤 Mantenedor Usuarios")
        options.append("⚙️ Maestro Productos")
    
    choice = st.sidebar.radio("Navegación", options)

    if st.sidebar.button("Log out"):
        del st.session_state.auth_user
        st.rerun()

    # --- ENRUTAMIENTO ---
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
        st.title("🔐 Acceso")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("INGRESAR"):
                # VALIDACIÓN: Admin (independiente de mayúsculas)
                if u.lower() == "admin" and p == "654321.":
                    st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}
                    st.success("¡Bienvenido Administrador!")
                    st.rerun()
                elif u != "" and p != "":
                    st.session_state.auth_user = {"user": u, "role": "Staff", "local": 1}
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")

def registro_pantalla(local_id):
    st.header("📥 Movimientos de Inventario")
    # (El resto del código de registro que ya teníamos)
    st.info("Aquí el personal registra entradas y salidas.")

def reportes_pantalla():
    st.header("📊 Reportes de Stock")
    st.write("Visualización consolidada por local y ubicación.")

def mantenedor_usuarios():
    st.header("👤 Gestión de Usuarios")
    st.write("Cree y gestione los accesos del personal.")
    # Implementaremos la creación real aquí

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    st.info("Carga el archivo Excel para actualizar la lista de productos.")
    file = st.file_uploader("Subir Maestro (.xlsx)", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        st.dataframe(df.head())
        if st.button("Actualizar Base de Datos"):
            data = df.to_dict(orient='records')
            supabase.table("productos_maestro").upsert(data).execute()
            st.success("Maestro actualizado.")

if __name__ == "__main__":
    main()
