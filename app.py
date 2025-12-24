import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Configura los Secrets en Streamlit Cloud.")
    st.stop()

# --- DISEÑO VISUAL MEJORADO (FONDO NEGRO / TEXTO BLANCO) ---
st.markdown("""
    <style>
    /* Fondo General */
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    
    /* Textos y Etiquetas */
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
    
    /* Botones de acción (Rojos) */
    .red-btn > div > button {
        background-color: #DD0000 !important;
        color: white !important;
    }
    
    h1, h2, h3 { color: #FFCC00 !important; }
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
        
    st.sidebar.markdown(f"**Usuario:** {user['user']} | **Rol:** {user['role']}")
    
    options = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin":
        options.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    
    choice = st.sidebar.radio("Menú", options)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    # NAVEGACIÓN
    if choice == "📥 Registro Movimiento":
        registro_pantalla(user['local'])
    elif choice == "👤 Mantenedor Usuarios":
        mantenedor_usuarios()
    elif choice == "⚙️ Maestro Productos":
        admin_panel()
    elif choice == "📊 Reportes":
        st.header("📊 Reportes de Stock")
        st.info("Visualización de inventario actual.")

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("Logo AE.jpg", width=250)
        except:
            st.title("ALEMAN EXPERTO")
            
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("INGRESAR")
            
            if submitted:
                # 1. Validar Super Administrador
                if u.lower() == "admin" and p == "654321.":
                    st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}
                    st.rerun()
                
                # 2. Validar contra Base de Datos
                else:
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute()
                    if res.data:
                        user_data = res.data[0]
                        st.session_state.auth_user = {
                            "user": user_data['usuario'], 
                            "role": user_data['rol'], 
                            "local": user_data['id_local']
                        }
                        st.rerun()
                    else:
                        st.error("🚫 Usuario no registrado o clave incorrecta.")

def registro_pantalla(local_id):
    st.header("📥 Registro de Movimiento")
    
    # Búsqueda integrada de productos
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("No hay productos cargados en el sistema.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Seleccionar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            peso = st.number_input(f"Cantidad recibida ({p['umb']}):", min_value=0.0)
            unid = st.selectbox("Unidad:", ["gramos", "kilos", "litros", "cc"])
        
        # Lógica de pesaje/conversión
        mult = 1000 if unid in ["kilos", "litros"] else 1
        total_umb = peso * mult

        st.markdown('<div class="red-btn">', unsafe_allow_html=True)
        if st.button("GUARDAR EN INVENTARIO"):
            ajuste = total_umb if tipo == "ENTRADA" else -total_umb
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id, "id_producto": p['id'], "cantidad": total_umb, 
                "tipo_movimiento": tipo, "ubicacion": ubi, "peso_verificado": peso, "unidad_peso_verificado": unid
            }).execute()
            st.success("✅ Registro guardado exitosamente.")
        st.markdown('</div>', unsafe_allow_html=True)

def mantenedor_usuarios():
    st.header("👤 Maestro de Usuarios")
    t1, t2 = st.tabs(["Añadir / Editar", "Ver Activos"])
    
    with t1:
        with st.form("user_form"):
            n = st.text_input("Nombre y Apellido")
            c = st.text_input("Correo")
            l = st.number_input("ID Local", min_value=1, step=1)
            u = st.text_input("Nombre de Usuario")
            p = st.text_input("Clave", type="password")
            r = st.selectbox("Rol", ["Staff", "Admin"])
            if st.form_submit_button("REGISTRAR USUARIO"):
                data = {"nombre_apellido": n, "correo": c, "id_local": l, "usuario": u, "clave": p, "rol": r}
                supabase.table("usuarios_sistema").upsert(data, on_conflict="usuario").execute()
                st.success(f"Usuario {u} gestionado con éxito.")

    with t2:
        usrs = supabase.table("usuarios_sistema").select("*").execute().data
        if usrs:
            df = pd.DataFrame(usrs)
            st.dataframe(df[["nombre_apellido", "usuario", "rol", "id_local"]], use_container_width=True)
            
            # Opción de borrar
            borrar = st.selectbox("Seleccionar para eliminar:", [x['usuario'] for x in usrs])
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("ELIMINAR USUARIO"):
                supabase.table("usuarios_sistema").delete().eq("usuario", borrar).execute()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    file = st.file_uploader("Subir Maestro (.xlsx)", type=["xlsx"])
    if file:
        df = pd.read_excel(file)
        if st.button("CARGAR MAESTRO"):
            # El script original se define como el "original"
            data = df.to_dict(orient='records')
            supabase.table("productos_maestro").upsert(data).execute()
            st.success("Base de datos actualizada.")

if __name__ == "__main__":
    main()

