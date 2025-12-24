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
    
    /* BOTÓN BLANCO: Texto negro y grueso */
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: 2px solid #FFCC00 !important;
    }
    
    .stSelectbox div[data-baseweb="select"] > div { background-color: #1A1A1A; color: white; border: 1px solid #FFCC00; }
    .stTextInput>div>div>input { background-color: #1A1A1A; color: white; border: 1px solid #333; }

    .red-btn > div > button {
        background-color: #DD0000 !important;
        color: #FFFFFF !important;
    }
    
    h1, h2, h3 { color: #FFCC00 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO ---
def get_locales_map():
    res = supabase.table("locales").select("id, nombre").execute().data
    return {l['nombre']: l['id'] for l in res} if res else {}

def get_stock_actual(producto_id, local_id):
    """Obtiene el stock neto acumulado en la base de datos"""
    res = supabase.table("movimientos_inventario").select("cantidad").eq("id_producto", producto_id).eq("id_local", local_id).execute().data
    return sum(item['cantidad'] for item in res) if res else 0

def extraer_valor_formato(formato_str):
    """Extrae el número de un string (ej: '750cc' -> 750)"""
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

# --- 4. PANTALLAS ---

def registro_pantalla(local_id):
    st.header("📥 Registro de Movimiento")
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    seleccion = st.selectbox("Buscar Producto:", [""] + list(prod_map.keys()))
    
    if seleccion:
        p = prod_map[seleccion]
        # Mostrar existencia en unidades físicas (botellas/unidades)
        stock_total_minimo = get_stock_actual(p['id'], local_id)
        factor = extraer_valor_formato(p['formato_medida'])
        stock_fisico = stock_total_minimo / factor if factor > 0 else 0
        
        st.info(f"Existencia actual: {stock_fisico} Unidades ({stock_total_minimo} {p['umb']})")
        
        col1, col2 = st.columns(2)
        with col1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Cámara de frío", "Producción", "Cocina"])
            tipo = st.radio("Operación:", ["ENTRADA", "SALIDA"])
        with col2:
            cantidad_ingresada = st.number_input("Cantidad:", min_value=0.0)
            unid = st.selectbox("Unidad:", ["Unitario", "gramos", "cc", "kilos", "litros"])
        
        # Lógica de conversión para guardar en la BD
        if unid == "Unitario":
            total_unidades_minimas = cantidad_ingresada * factor
        else:
            mult = 1000 if unid in ["kilos", "litros"] else 1
            total_unidades_minimas = cantidad_ingresada * mult

        if st.button("CONFIRMAR MOVIMIENTO"):
            if tipo == "SALIDA" and total_unidades_minimas > stock_total_minimo:
                st.error(f"❌ Stock insuficiente.")
            elif cantidad_ingresada > 0:
                valor_final = total_unidades_minimas if tipo == "ENTRADA" else -total_unidades_minimas
                supabase.table("movimientos_inventario").insert({
                    "id_local": local_id, "id_producto": p['id'], "cantidad": valor_final, "tipo_movimiento": tipo, "ubicacion": ubi
                }).execute()
                st.success("✅ Inventario actualizado.")
                st.rerun()

def reportes_pantalla(locales_dict):
    st.header("📊 Reportes de Inventario")
    filtro = st.selectbox("Sede:", ["Todos"] + list(locales_dict.keys()))
    query = supabase.table("movimientos_inventario").select("cantidad, id_local, productos_maestro(nombre, formato_medida, umb)")
    if filtro != "Todos": query = query.eq("id_local", locales_dict[filtro])
    
    data = query.execute().data
    if data:
        df = pd.json_normalize(data)
        df_stock = df.groupby(['productos_maestro.nombre', 'productos_maestro.formato_medida', 'productos_maestro.umb']).agg({'cantidad': 'sum'}).reset_index()
        
        # LÓGICA SOLICITADA:
        # Stock = Unidades físicas (ej: 8 botellas)
        # StockUMB = Cálculo total (ej: 6000 cc)
        df_stock['factor'] = df_stock['productos_maestro.formato_medida'].apply(extraer_valor_formato)
        df_stock['Stock'] = df_stock['cantidad'] / df_stock['factor']
        df_stock['StockUMB'] = df_stock['Stock'] * df_stock['factor']
        
        # Selección de columnas finales
        df_final = df_stock[['productos_maestro.nombre', 'productos_maestro.formato_medida', 'Stock', 'productos_maestro.umb', 'StockUMB']]
        df_final.columns = ['Producto', 'Formato', 'Stock', 'UMB', 'StockUMB']
        
        st.dataframe(df_final, use_container_width=True)

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
                supabase.table("usuarios_sistema").upsert({
                    "nombre_apellido": n, "id_local": locales_dict[l_sel], "usuario": u, "clave": p, "rol": r
                }, on_conflict="usuario").execute()
                st.success("Usuario procesado.")
    with t2:
        res = supabase.table("usuarios_sistema").select("*").execute().data
        if res:
            df = pd.DataFrame(res)
            user_del = st.selectbox("Eliminar a:", df["usuario"])
            if st.button("ELIMINAR DEFINITIVAMENTE"):
                supabase.table("usuarios_sistema").delete().eq("usuario", user_del).execute()
                st.rerun()

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
    menu = ["📥 Registro Movimiento", "📊 Reportes"]
    if user['role'] == "Admin": menu.extend(["👤 Mantenedor Usuarios", "⚙️ Maestro Productos"])
    choice = st.sidebar.radio("Navegación", menu)

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth_user
        st.rerun()

    if choice == "📥 Registro Movimiento": registro_pantalla(user['local'])
    elif choice == "📊 Reportes": reportes_pantalla(locales_dict)
    elif choice == "👤 Mantenedor Usuarios": mantenedor_usuarios(locales_dict)
    elif choice == "⚙️ Maestro Productos": admin_panel()

if __name__ == "__main__":
    main()
