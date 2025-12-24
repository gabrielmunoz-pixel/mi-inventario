import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURACIÓN DE SUPABASE ---
# Reemplaza con tus datos de "Project Settings > API"
URL = "https://wjnygzrvmzxtefvpubsa.supabase.co"
KEY = "sb_publishable_A9nvq3yMs1qyvFrj6IM2Qg_ERkRURrf" 
supabase: Client = create_client(URL, KEY)

def main():
    st.set_page_config(page_title="Inventario Restaurantes", layout="wide")
    
    if 'auth_user' not in st.session_state:
        st.title("🛡️ Acceso Inventario")
        user = st.text_input("Nombre de Usuario")
        role = st.selectbox("Rol", ["Staff", "Admin"])
        local_id = st.number_input("ID de Local asignado", min_value=1, step=1)
        
        if st.button("Ingresar Sistema"):
            st.session_state.auth_user = {"user": user, "role": role, "local": local_id}
            st.rerun()
        return

    user_data = st.session_state.auth_user
    st.sidebar.title(f"Bienvenido {user_data['user']}")
    if st.sidebar.button("Log out"):
        del st.session_state.auth_user
        st.rerun()

    if user_data['role'] == "Admin":
        admin_panel()
    else:
        staff_panel(user_data['local'])

def admin_panel():
    st.header("⚙️ Panel de Administrador")
    st.subheader("Carga Masiva de Productos (Maestro)")
    uploaded_file = st.file_uploader("Subir Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Vista previa de carga:", df.head())
        if st.button("Confirmar Carga"):
            data = df.to_dict(orient='records')
            # Usamos el script original definido como "original" para esta operación
            supabase.table("productos_maestro").upsert(data).execute()
            st.success("✅ Maestro de productos actualizado.")

def staff_panel(local_id):
    st.header(f"📦 Movimientos Local #{local_id}")

    # Obtener lista de productos
    prods = supabase.table("productos_maestro").select("id, nombre").execute().data
    prod_options = {p['nombre']: p['id'] for p in prods}
    
    with st.form("movimiento"):
        item_nom = st.selectbox("Producto", list(prod_options.keys()))
        cant = st.number_input("Cantidad", min_value=0.1)
        tipo = st.radio("Operación", ["ENTRADA", "SALIDA"])
        nota = st.text_input("Nota/Observación")
        submit = st.form_submit_button("Registrar")

    if submit:
        p_id = prod_options[item_nom]
        cambio = cant if tipo == "ENTRADA" else -cant
        
        # 1. Registrar Auditoría
        supabase.table("movimientos_inventario").insert({
            "id_local": local_id,
            "id_producto": p_id,
            "tipo_movimiento": tipo,
            "cantidad": cant,
            "nota": nota
        }).execute()

        # 2. Actualizar Stock Real
        stock_data = supabase.table("stock_config").select("*").eq("id_local", local_id).eq("id_producto", p_id).execute().data
        
        if stock_data:
            nuevo_total = float(stock_data[0]['stock_actual']) + cambio
            supabase.table("stock_config").update({"stock_actual": nuevo_total}).eq("id", stock_data[0]['id']).execute()
        else:
            nuevo_total = cambio
            supabase.table("stock_config").insert({"id_local": local_id, "id_producto": p_id, "stock_actual": nuevo_total, "stock_minimo": 5}).execute()
        
        st.success(f"Movimiento registrado. Nuevo Stock: {nuevo_total}")

    # 3. Alertas
    st.divider()
    alertas = supabase.table("stock_config").select("*, productos_maestro(nombre)").eq("id_local", local_id).execute().data
    for a in alertas:
        if a['stock_actual'] <= a['stock_minimo']:
            st.error(f"🚨 **BAJO STOCK**: {a['productos_maestro']['nombre']} tiene {a['stock_actual']} unidades.")

if __name__ == "__main__":
    main()