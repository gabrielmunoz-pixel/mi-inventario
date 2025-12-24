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

# --- ESTILO VISUAL "ALEMAN EXPERTO" ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span { color: #FFFFFF !important; }
    
    /* Input y Selectbox */
    .stSelectbox div[data-baseweb="select"] > div { background-color: #222222; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #222222; color: white; border: 1px solid #333; }
    
    /* BOTÓN LOGIN: Fondo blanco, letras negras como pediste */
    .login-btn > div > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: none !important;
    }

    /* BOTONES GENERALES (Rojos) */
    .stButton>button { background-color: #DD0000; color: white; border-radius: 5px; font-weight: bold; }
    
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    try:
        st.sidebar.image("Logo AE.jpg", use_container_width=True)
    except:
        st.sidebar.title("🇩🇪 AE")
        
    st.sidebar.markdown(f"**Usuario:** {user['user']} | **Rol:** {user['role']}")
    
    options = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin":
        options.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    
    choice = st.sidebar.radio("Navegación", options)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    # ENRUTAMIENTO
    if choice == "📥 Registro Movimiento":
        registro_pantalla(user['local'])
    elif choice == "📊 Reportes":
        st.header("📊 Reportes en desarrollo")
    elif choice == "👤 Mantenedor Usuarios":
        mantenedor_usuarios()
    elif choice == "⚙️ Maestro Productos":
        admin_panel()

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("Logo AE.jpg", width=250) if "Logo" else st.title("ALEMAN EXPERTO")
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            # Usamos un div para aplicar el estilo de botón blanco
            st.markdown('<div class="login-btn">', unsafe_allow_html=True)
            submitted = st.form_submit_button("INGRESAR")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if submitted:
                if u.lower() == "admin" and p == "654321.":
                    st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}
                    st.rerun()
                else:
                    # Buscar en tabla usuarios_sistema
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute()
                    if res.data:
                        st.session_state.auth_user = {"user": u, "role": res.data[0]['rol'], "local": res.data[0]['id_local']}
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")

def registro_pantalla(local_id):
    st.header("📥 Registro de Movimiento")
    
    # Restauramos la búsqueda de productos
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("Carga productos en el Maestro primero.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Buscar y Seleccionar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        st.info(f"Unidad Base: {p['umb']} | Factor: {p['factor_conversion']}")
        
        col1, col2 = st.columns(2)
        with col1:
            ubicacion = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            peso = st.number_input("Peso/Cant. recibida:", min_value=0.0)
            unid = st.selectbox("Unidad:", ["gramos", "kilos", "litros", "cc"])
        
        # Conversión automática
        mult = 1000 if unid in ["kilos", "litros"] else 1
        total_umb = peso * mult

        if st.button("GUARDAR MOVIMIENTO"):
            ajuste = total_umb if tipo == "ENTRADA" else -total_umb
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id, "id_producto": p['id'], "cantidad": total_umb, 
                "tipo_movimiento": tipo, "ubicacion": ubicacion, "peso_verificado": peso, "unidad_peso_verificado": unid
            }).execute()
            st.success(f"✅ Guardado: {total_umb} {p['umb']} en {ubicacion}")

def mantenedor_usuarios():
    st.header("👤 Gestión de Usuarios")
    
    tab1, tab2 = st.tabs(["➕ Crear / Modificar", "📋 Lista de Usuarios"])
    
    with tab1:
        with st.form("form_usuario"):
            nom = st.text_input("Nombre y Apellido")
            mail = st.text_input("Correo")
            loc = st.number_input("ID Local", min_value=1, step=1)
            usr = st.text_input("Nombre de Usuario (Login)")
            pwd = st.text_input("Clave", type="password")
            rol = st.selectbox("Rol", ["Staff", "Admin"])
            if st.form_submit_button("GUARDAR USUARIO"):
                data = {"nombre_apellido": nom, "correo": mail, "id_local": loc, "usuario": usr, "clave": pwd, "rol": rol}
                supabase.table("usuarios_sistema").upsert(data, on_conflict="usuario").execute()
                st.success(f"Usuario {usr} actualizado con éxito.")

    with tab2:
        usuarios = supabase.table("usuarios_sistema").select("*").execute().data
        if usuarios:
            df_usr = pd.DataFrame(usuarios)
            st.dataframe(df_usr[["nombre_apellido", "usuario", "rol", "id_local", "correo"]], use_container_width=True)
            
            user_del = st.selectbox("Seleccionar usuario para borrar", [u['usuario'] for u in usuarios])
            if st.button("BORRAR SELECCIONADO"):
                supabase.table("usuarios_sistema").delete().eq("usuario", user_del).execute()
                st.warning(f"Usuario {user_del} eliminado.")
                st.rerun()

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    file = st.file_uploader("Subir Excel (.xlsx)", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        st.dataframe(df.head())
        if st.button("PROCESAR CARGA"):
            supabase.table("productos_maestro").upsert(df.to_dict(orient='records')).execute()
            st.success("Base de datos de productos actualizada.")

if __name__ == "__main__":
    main()
