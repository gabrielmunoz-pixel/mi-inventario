import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Revisa los Secrets en Streamlit.")
    st.stop()

# --- DISEÑO VISUAL (CORRECCIÓN DE BOTONES Y COLORES) ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span, .stHeader { color: #FFFFFF !important; }
    
    /* Input y Selectores */
    .stSelectbox div[data-baseweb="select"] > div { background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #1A1A1A; color: white; border: 1px solid #333; }
    
    /* BOTONES CLAROS (Login/Logout): Letra Negra para legibilidad */
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border: none !important;
    }
    
    /* BOTONES DE ACCIÓN (Guardar/Eliminar): Rojos */
    .red-btn > div > button {
        background-color: #DD0000 !important;
        color: #FFFFFF !important;
    }
    
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE DATOS ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def get_stock_actual(producto_id, local_id):
    res = supabase.table("movimientos_inventario").select("cantidad").eq("id_producto", producto_id).eq("id_local", local_id).execute().data
    return sum(item['cantidad'] for item in res) if res else 0

# --- PANTALLAS ---

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("Logo AE.jpg", width=250)
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("INGRESAR"):
                if u.lower() == "admin" and p == "654321.":
                    st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1} # Default 1 para admin
                    st.rerun()
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
                        st.error("🚫 Credenciales incorrectas.")

def registro_pantalla(local_id):
    st.header("📥 Movimiento de Inventario")
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Seleccionar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        stock_disponible = get_stock_actual(p['id'], local_id)
        st.info(f"Stock Actual en este local: {stock_disponible} {p['umb']}")
        
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            peso = st.number_input("Cantidad:", min_value=0.0)
            unid = st.selectbox("Unidad:", ["gramos", "kilos", "litros", "cc", "Unitario"])
        
        # Conversión
        mult = 1000 if unid in ["kilos", "litros"] else 1
        total_umb = peso * mult

        st.markdown('<div class="red-btn">', unsafe_allow_html=True)
        if st.button("CONFIRMAR MOVIMIENTO"):
            if tipo == "SALIDA" and total_umb > stock_disponible:
                st.error(f"❌ Stock Insuficiente. Intentas sacar {total_umb} pero solo hay {stock_disponible}.")
            else:
                valor_final = total_umb if tipo == "ENTRADA" else -total_umb
                supabase.table("movimientos_inventario").insert({
                    "id_local": local_id, "id_producto": p['id'], "cantidad": valor_final, 
                    "tipo_movimiento": tipo, "ubicacion": ubi
                }).execute()
                st.success("✅ Inventario actualizado.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla(locales_dict):
    st.header("📊 Stock Consolidado")
    loc_options = ["Todos"] + list(locales_dict.keys())
    filtro = st.selectbox("Filtrar por Sede:", loc_options)
    
    query = supabase.table("movimientos_inventario").select("cantidad, id_local, productos_maestro(nombre, formato_medida, umb)")
    if filtro != "Todos":
        query = query.eq("id_local", locales_dict[filtro])
    
    data = query.execute().data
    if data:
        df = pd.json_normalize(data)
        df_stock = df.groupby(['productos_maestro.nombre', 'productos_maestro.formato_medida', 'productos_maestro.umb']).agg({'cantidad': 'sum'}).reset_index()
        df_stock.columns = ['Producto', 'Formato', 'UMB', 'Existencia']
        st.table(df_stock)
    else:
        st.info("Sin registros.")

# --- MAIN ---
def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    locales_dict = get_locales_map()
    locales_inv = {v: k for k, v in locales_dict.items()}

    # SIDEBAR
    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    
    # Lógica de cambio de local para ADMIN
    if user['role'] == "Admin":
        st.sidebar.subheader("⚙️ Panel Admin")
        nuevo_local = st.sidebar.selectbox("Cambiar Sede Activa:", list(locales_dict.keys()), 
                                          index=list(locales_dict.values()).index(user['local']))
        user['local'] = locales_dict[nuevo_local]
    
    st.sidebar.markdown(f"**Sede Actual:** {locales_inv.get(user['local'])}")
    
    menu = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin":
        menu.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    
    choice = st.sidebar.radio("Navegación", menu)

    if st.sidebar.button("Log Out"):
        del st.session_state.auth_user
        st.rerun()

    if choice == "📥 Registro Movimiento":
        registro_pantalla(user['local'])
    elif choice == "📊 Reportes":
        reportes_pantalla(locales_dict)
    elif choice == "👤 Mantenedor Usuarios":
        # (Aquí iría la función de mantenedor de usuarios que ya revisamos)
        pass
    elif choice == "⚙️ Maestro Productos":
        # (Aquí iría la función de maestro de productos que ya revisamos)
        pass

if __name__ == "__main__":
    main()
