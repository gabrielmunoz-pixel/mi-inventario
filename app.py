import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CIBERSEGURIDAD: CARGA DE SECRETS ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Error de configuración: Verifica los Secrets en Streamlit Cloud.")
    st.stop()

# --- DISEÑO VISUAL "ALEMAN EXPERTO" ---
st.markdown("""
    <style>
    /* Fondo oscuro y fuentes */
    .stApp { background-color: #111827; color: #F3F4F6; }
    .stSidebar { background-color: #1F2937; }
    
    /* Encabezados con color Dorado/Amarillo del logo */
    h1, h2, h3 { color: #FFCC00 !important; font-family: 'Inter', sans-serif; }
    
    /* Estilo de tarjetas (Cards) como en tu ejemplo */
    .stMetric {
        background-color: #374151;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #DD0000; /* Rojo Alemán */
    }
    
    /* Botones personalizados */
    .stButton>button {
        background-color: #DD0000;
        color: white;
        border: none;
        width: 100%;
        font-weight: bold;
    }
    .stButton>button:hover { background-color: #FF0000; color: white; }
    </style>
    """, unsafe_allow_html=True)

def main():
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    
    # Barra lateral con navegación
    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    st.sidebar.markdown(f"**Usuario:** {user['user']} | **Local:** {user['local']}")
    
    menu = ["📊 Dashboard", "📥 Movimientos", "⚙️ Maestro de Productos"]
    choice = st.sidebar.radio("Navegación", menu)

    if choice == "📊 Dashboard":
        dashboard_consolidado()
    elif choice == "📥 Movimientos":
        movimientos_screen(user['local'])
    elif choice == "⚙️ Maestro de Productos":
        admin_panel()

def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("Logo AE.jpg", width=250)
        except:
            st.title("🇩🇪 ALEMAN EXPERTO")
        
        with st.form("Login"):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password") # Seguridad básica
            local = st.number_input("ID Local", min_value=1, step=1, value=1)
            if st.form_submit_button("INICIAR SESIÓN"):
                st.session_state.auth_user = {"user": user, "local": local}
                st.rerun()

def dashboard_consolidado():
    st.header("📊 Dashboard de Inventario")
    # Métricas rápidas (Estilo tarjetas del ejemplo)
    c1, c2, c3 = st.columns(3)
    c1.metric("Items en Crítico", "12", delta="-2", delta_color="inverse")
    c2.metric("Movimientos Hoy", "45")
    c3.metric("Valor Inventario", "$1.2M")

    st.subheader("Stock Actual Global")
    # Consulta a stock_config con join a productos_maestro
    data = supabase.table("stock_config").select("*, productos_maestro(*)").execute().data
    if data:
        df = pd.json_normalize(data)
        # Limpieza de nombres de columnas para el usuario
        df_view = df[['id_local', 'productos_maestro.nombre', 'stock_actual', 'productos_maestro.umb']]
        st.dataframe(df_view, use_container_width=True)

def movimientos_screen(local_id):
    st.header(f"📥 Registro de Movimiento - Local {local_id}")
    
    # Búsqueda por proximidad
    search = st.text_input("🔍 Buscar Producto por nombre...")
    res = supabase.table("productos_maestro").select("*").ilike("nombre", f"%{search}%").execute().data
    
    if res:
        options = {f"{r['nombre']} ({r['formato_medida']})": r for r in res}
        sel_name = st.selectbox("Seleccione el producto exacto", list(options.keys()))
        p = options[sel_name]
        
        st.markdown(f"**Unidad Base:** {p['umb']} | **Factor:** {p['factor_conversion']}")
        
        col1, col2 = st.columns(2)
        with col1:
            modo = st.radio("Formato de entrada", [f"Unidad de Compra ({p['unidad_compra']})", f"Unidad Base ({p['umb']})"])
            cant_user = st.number_input("Cantidad", min_value=0.0)
        
        # CALCULADORA DE CONVERSIÓN
        total_final = cant_user * float(p['factor_conversion']) if "Unidad de Compra" in modo else cant_user
        
        with col2:
            tipo = st.selectbox("Tipo", ["ENTRADA", "SALIDA"])
            st.metric("Total a procesar", f"{total_final} {p['umb']}")

        if st.button("REGISTRAR EN INVENTARIO"):
            ajuste = total_final if tipo == "ENTRADA" else -total_final
            # Registro en logs
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id, "id_producto": p['id'], "cantidad": total_final, "tipo_movimiento": tipo
            }).execute()
            # Actualización de stock_config
            curr = supabase.table("stock_config").select("stock_actual").eq("id_local", local_id).eq("id_producto", p['id']).execute().data
            if curr:
                nuevo = float(curr[0]['stock_actual']) + ajuste
                supabase.table("stock_config").update({"stock_actual": nuevo}).eq("id_local", local_id).eq("id_producto", p['id']).execute()
            else:
                supabase.table("stock_config").insert({"id_local": local_id, "id_producto": p['id'], "stock_actual": ajuste}).execute()
            st.success("✅ Registro completado exitosamente.")

def admin_panel():
    st.header("⚙️ Gestión del Maestro de Productos")
    uploaded_file = st.file_uploader("Cargar Excel Maestro", type=["xlsx"])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Vista previa de carga:", df.head())
        if st.button("Confirmar Carga Masiva"):
            # El script original se define como el "original"
            data = df.to_dict(orient='records')
            supabase.table("productos_maestro").upsert(data).execute()
            st.success("Maestro actualizado.")

if __name__ == "__main__":
    main()
