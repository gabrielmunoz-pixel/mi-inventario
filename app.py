import streamlit as st
import pandas as pd
import re
from supabase import create_client, Client

# --- 1. CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error: Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- 2. DISEÑO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown, p, label, .stMetric, span, .stHeader, .stTab { color: #FFFFFF !important; }
    
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: 2px solid #FFCC00 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div { background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #1A1A1A; color: white; border: 1px solid #333; }

    .red-btn > div > button { background-color: #DD0000 !important; color: #FFFFFF !important; }
    .green-btn > div > button { background-color: #28a745 !important; color: #FFFFFF !important; }
    
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

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

# --- 4. PANTALLAS ---

def registro_pantalla(local_id):
    st.header("📥 Registro por Sesión")
    
    # Inicializar el "carrito" de la sesión si no existe
    if 'carrito_inventario' not in st.session_state:
        st.session_state.carrito_inventario = []

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    
    # Buscador para teclado móvil
    busqueda = st.text_input("🔍 Buscar producto:", placeholder="Escribe para filtrar...")
    opciones = [opc for opc in prod_map.keys() if busqueda.lower() in opc.lower()]
    seleccion = st.selectbox("Selecciona producto:", [""] + opciones)
    
    if seleccion:
        p = prod_map[seleccion]
        stock_total_minimo = get_stock_actual(p['id'], local_id)
        factor = extraer_valor_formato(p['formato_medida'])
        st.info(f"Stock actual: {round(stock_total_minimo/factor, 2)} Unidades")
        
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            cant = st.number_input("Cantidad:", min_value=0.0, step=1.0)
            unid = st.selectbox("Unidad:", ["Unitario", "gramos", "cc", "kilos", "litros"])
        
        if st.button("AÑADIR A LA LISTA"):
            mult = 1000 if unid in ["kilos", "litros"] else 1
            total_umb = (cant * factor) if unid == "Unitario" else (cant * mult)
            
            # Guardar en memoria temporal
            item = {
                "id_producto": p['id'],
                "Producto": p['nombre'],
                "Ubicación": ubi,
                "Tipo": tipo,
                "Cantidad": cant,
                "Unidad": unid,
                "TotalUMB": total_umb if tipo == "ENTRADA" else -total_umb
            }
            st.session_state.carrito_inventario.append(item)
            st.toast(f"Añadido: {p['nombre']}")

    # --- VISTA PREVIA Y EDICIÓN ---
    if st.session_state.carrito_inventario:
        st.subheader("📝 Vista Previa de la Sesión")
        df_temp = pd.DataFrame(st.session_state.carrito_inventario)
        
        # Permitir editar la lista antes de cargar
        edited_df = st.data_editor(df_temp, num_rows="dynamic", use_container_width=True)
        
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("✅ CARGAR TODO A BASE DE DATOS"):
                for row in edited_df.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({
                        "id_local": local_id,
                        "id_producto": row['id_producto'],
                        "cantidad": row['TotalUMB'],
                        "tipo_movimiento": row['Tipo'],
                        "ubicacion": row['Ubicación']
                    }).execute()
                st.session_state.carrito_inventario = []
                st.success("¡Inventario cargado exitosamente!")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_cancel:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR SESIÓN"):
                st.session_state.carrito_inventario = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reportes_pantalla(locales_dict):
    st.header("📊 Reportes de Inventario")
    filtro = st.selectbox("Sede:", ["Todos"] + list(locales_dict.keys()))
    query = supabase.table("movimientos_inventario").select("id, created_at, cantidad, id_local, productos_maestro(nombre, formato_medida, umb)")
    if filtro != "Todos": query = query.eq("id_local", locales_dict[filtro])
    
    data = query.execute().data
    if data:
        df = pd.json_normalize(data)
        
        # HISTORIAL DETALLADO (Editable)
        with st.expander("🕒 Ver Historial de Movimientos (Editar/Borrar)"):
            df_hist = df.copy()
            # Simplificar columnas para el usuario
            df_hist = df_hist[['id', 'created_at', 'productos_maestro.nombre', 'cantidad']]
            df_hist.columns = ['ID', 'Fecha', 'Producto', 'ValorUMB']
            
            edited_hist = st.data_editor(df_hist, use_container_width=True, key="hist_editor")
            
            if st.button("ACTUALIZAR HISTORIAL"):
                for row in edited_hist.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").update({"cantidad": row['ValorUMB']}).eq("id", row['ID']).execute()
                st.success("Historial actualizado.")

        # Resumen de Stock
        df_stock = df.groupby(['productos_maestro.nombre', 'productos_maestro.formato_medida', 'productos_maestro.umb']).agg({'cantidad': 'sum'}).reset_index()
        df_stock['factor'] = df_stock['productos_maestro.formato_medida'].apply(extraer_valor_formato)
        df_stock['Stock'] = (df_stock['cantidad'] / df_stock['factor']).round(2)
        df_stock['StockUMB'] = df_stock['cantidad'].round(2)
        
        df_final = df_stock[['productos_maestro.nombre', 'productos_maestro.formato_medida', 'Stock', 'productos_maestro.umb', 'StockUMB']]
        df_final.columns = ['Producto', 'Formato', 'Stock', 'UMB', 'StockUMB']
        st.dataframe(df_final, use_container_width=True)

# --- LAS DEMÁS FUNCIONES (mantenedor_usuarios, admin_panel, main) SE MANTIENEN IGUAL QUE ANTES ---

def mantenedor_usuarios(locales_dict):
    st.header("👤 Gestión de Usuarios")
    t1, t2 = st.tabs(["Crear / Editar", "Borrar Usuario"])
    with t1:
        with st.form("UserForm"):
            n = st.text_input("Nombre y Apellido")
            l_sel = st.selectbox("Local Asignado", list(locales_dict.keys()))
            u = st.text_input("Usuario")
            p = st.text_input("Clave")
            r = st.selectbox("Rol", ["Staff", "Admin"])
            if st.form_submit_button("GUARDAR / ACTUALIZAR"):
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": locales_dict[l_sel], "usuario": u, "clave": p, "rol": r}, on_conflict="usuario").execute()
                st.success("Usuario procesado.")
    with t2:
        res = supabase.table("usuarios_sistema").select("*").execute().data
        if res:
            df = pd.DataFrame(res)
            user_del = st.selectbox("Eliminar a:", df["usuario"])
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("ELIMINAR DEFINITIVAMENTE"):
                supabase.table("usuarios_sistema").delete().eq("usuario", user_del).execute()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def admin_panel():
    st.header("⚙️ Maestro de Productos")
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        df_prod = pd.DataFrame(res)
        edited_df = st.data_editor(df_prod, num_rows="dynamic", use_container_width=True)
        if st.button("GUARDAR CAMBIOS"):
            supabase.table("productos_maestro").upsert(edited_df.to_dict(orient='records')).execute()
            st.success("Base de datos actualizada.")

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
        nuevo_local = st.sidebar.selectbox("Local Activo:", list(locales_dict.keys()), index=list(locales_dict.keys()).index(current_name))
        user['local'] = locales_dict[nuevo_local]

    st.sidebar.markdown(f"**Usuario:** {user['user']} | **Sede:** {locales_inv.get(user['local'])}")
    menu = ["📥 Registro Movimiento", "📊 Reportes", "👤 Mantenedor Usuarios", "⚙️ Maestro Productos"]
    actual_menu = menu if user['role'] == "Admin" else menu[:2]
    choice = st.sidebar.radio("Navegación", actual_menu)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    if choice == "📥 Registro Movimiento": registro_pantalla(user['local'])
    elif choice == "📊 Reportes": reportes_pantalla(locales_dict)
    elif choice == "👤 Mantenedor Usuarios": mantenedor_usuarios(locales_dict)
    elif choice == "⚙️ Maestro Productos": admin_panel()

if __name__ == "__main__":
    main()
