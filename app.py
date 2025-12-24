import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURACIÓN DE SUPABASE ---
# Reemplaza con tus datos de "Project Settings > API"
URL = "https://wjnygzrvmzxtefvpubsa.supabase.co"
KEY = "sb_publishable_A9nvq3yMs1qyvFrj6IM2Qg_ERkRURrf" 
supabase: Client = create_client(URL, KEY)

# Colores del Logo AE: Negro (#000000), Rojo (#DD0000), Dorado/Amarillo (#FFCC00)
st.markdown(f"""
    <style>
    .main {{ background-color: #f5f5f5; }}
    .stButton>button {{ background-color: #DD0000; color: white; border-radius: 8px; }}
    .stTextInput>div>div>input {{ border: 1px solid #000000; }}
    .stHeader {{ color: #000000; border-bottom: 2px solid #FFCC00; }}
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🇩🇪 ALEMAN EXPERTO - Gestión de Inventario")
    
    if 'auth_user' not in st.session_state:
        login_screen()
        return

    user = st.session_state.auth_user
    menu = ["📥 Registro de Movimientos", "📊 Stock Global", "⚙️ Configurar Maestro"]
    choice = st.sidebar.selectbox("Menú", menu)

    if choice == "📥 Registro de Movimientos":
        movimientos_screen(user['local'])
    elif choice == "📊 Stock Global":
        st.header("Stock Consolidado")
        # Aquí va la tabla de reporte que ya teníamos
    elif choice == "⚙️ Configurar Maestro":
        admin_panel()

def movimientos_screen(local_id):
    st.header(f"Entrada/Salida - Local {local_id}")
    
    # BÚSQUEDA POR PROXIMIDAD
    search_query = st.text_input("🔍 Buscar producto (ej: 'Pisco', 'Lechuga')...")
    
    # Obtener productos que coincidan
    prods_query = supabase.table("productos_maestro").select("*").ilike("nombre", f"%{search_query}%").execute()
    prods = prods_query.data

    if prods:
        # Mostramos opciones amigables
        opciones = {f"{p['nombre']} | {p['formato_medida']} ({p['unidad_compra']})": p for p in prods}
        seleccion = st.selectbox("Seleccione el resultado:", list(opciones.keys()))
        p = opciones[seleccion]

        st.info(f"**Ficha del Producto:** Categoría: {p['categoria']} | Vive en: {p['umb']} | Factor: {p['factor_conversion']}")

        col1, col2 = st.columns(2)
        with col1:
            modo = st.radio("Tipo de Ingreso", ["Por Unidad de Compra (Cajas/Paquetes)", "Por Medida Base (Gramos/CC)"])
            cantidad_input = st.number_input("Cantidad a ingresar", min_value=0.0, step=0.1)
        
        # CALCULADORA INTERNA
        if modo == "Por Unidad de Compra (Cajas/Paquetes)":
            total_umb = cantidad_input * float(p['factor_conversion'])
            st.success(f"Equivale a: **{total_umb} {p['umb']}**")
        else:
            total_umb = cantidad_input

        tipo_mov = st.selectbox("Movimiento", ["ENTRADA", "SALIDA"])
        
        if st.button("Confirmar Registro"):
            valor_final = total_umb if tipo_mov == "ENTRADA" else -total_umb
            
            # 1. Registro Log
            supabase.table("movimientos_inventario").insert({
                "id_local": local_id, "id_producto": p['id'], "cantidad": total_umb, "tipo_movimiento": tipo_mov
            }).execute()

            # 2. Update Stock (Siempre en UMB)
            curr = supabase.table("stock_config").select("stock_actual").eq("id_local", local_id).eq("id_producto", p['id']).execute().data
            if curr:
                nuevo = float(curr[0]['stock_actual']) + valor_final
                supabase.table("stock_config").update({"stock_actual": nuevo}).eq("id_local", local_id).eq("id_producto", p['id']).execute()
            else:
                supabase.table("stock_config").insert({"id_local": local_id, "id_producto": p['id'], "stock_actual": valor_final}).execute()
            
            st.balloons()
            st.success("Inventario actualizado.")

def login_screen():
    # Centrar el logo y el login
    st.image("Logo AE.jpg", width=200)
    user = st.text_input("Usuario")
    local = st.number_input("Local", value=1)
    if st.button("Entrar"):
        st.session_state.auth_user = {"user": user, "local": local}
        st.rerun()

if __name__ == "__main__":
    main()
