import streamlit as st
import pandas as pd
import re
import json
from datetime import datetime
from supabase import create_client, Client
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN Y CONEXIÓN
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# 2. GESTIÓN DE SESIÓN
def sync_session():
    params = st.query_params
    if "user_data" in params and "auth_user" not in st.session_state:
        try: 
            st.session_state.auth_user = json.loads(params["user_data"])
        except: 
            pass
    if "auth_user" in st.session_state:
        st.query_params["user_data"] = json.dumps(st.session_state.auth_user)

def logout():
    if "auth_user" in st.session_state: 
        del st.session_state.auth_user
    if "carritos" in st.session_state: 
        st.session_state.carritos = {}
    st.query_params.clear()
    st.rerun()

# 3. ESTILOS
st.markdown("""
    <style>
    .stApp { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #333; }
    .stMarkdown p, label p, .stHeader h1, .stHeader h2 { color: #FFFFFF !important; }
    div.stButton > button { background-color: #FFCC00 !important; color: #000000 !important; font-weight: bold; border-radius: 10px; width: 100%; }
    .nav-active > div > button { background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #FFCC00 !important; }
    .red-btn > div > button { background-color: #DD0000 !important; color: white !important; }
    .green-btn > div > button { background-color: #28a745 !important; color: white !important; }
    .user-info { font-family: monospace; color: #FFCC00; font-size: 12px; padding: 10px; border-bottom: 1px solid #333; }
    iframe { max-width: 450px !important; display: block; margin: 0 auto; border: 1px solid #444; border-radius: 15px; background: #000; }
    </style>
    """, unsafe_allow_html=True)

# 4. FUNCIONES DE APOYO
def get_locales_map():
    try:
        res = supabase.table("locales").select("id, nombre").execute().data
        return {l['nombre']: l['id'] for l in res} if res else {}
    except: 
        return {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

def obtener_stock_dict(local_id):
    try:
        res = supabase.table("movimientos_inventario").select("id_producto, cantidad").eq("id_local", local_id).execute().data
        if not res: return {}
        df = pd.DataFrame(res)
        return df.groupby("id_producto")["cantidad"].sum().to_dict()
    except: 
        return {}

# 5. COMPONENTE CALCULADORA (El "Original" con JS mejorado para Streamlit)
def calculadora_basica():
    calc_html = """
    <div id="calc-container" style="background: #000; padding: 10px; border-radius: 15px; font-family: sans-serif;">
        <div id="display" style="background: #1e1e1e; color: #00ff00; padding: 15px; text-align: right; font-size: 28px; border-radius: 10px; margin-bottom: 15px; min-height: 40px; border: 2px solid #333;">0</div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
            <button onclick="press('7')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">7</button>
            <button onclick="press('8')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">8</button>
            <button onclick="press('9')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">9</button>
            <button onclick="press('/')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">/</button>
            <button onclick="press('4')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">4</button>
            <button onclick="press('5')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">5</button>
            <button onclick="press('6')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">6</button>
            <button onclick="press('*')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">*</button>
            <button onclick="press('1')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">1</button>
            <button onclick="press('2')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">2</button>
            <button onclick="press('3')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">3</button>
            <button onclick="press('-')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">-</button>
            <button onclick="press('0')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">0</button>
            <button onclick="press('.')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px;">.</button>
            <button onclick="solve()" style="height: 45px; background: #1A73E8; color: white; border: none; border-radius: 8px;">=</button>
            <button onclick="press('+')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">+</button>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
            <button onclick="clearCalc()" style="padding: 12px; background: #440000; color: white; border: none; border-radius: 8px;">Limpiar</button>
            <button onclick="sendResult()" style="padding: 12px; background: #1A73E8; color: white; border: none; border-radius: 8px; font-weight: bold;">LISTO</button>
        </div>
    </div>
    <script>
        let current = "";
        const display = document.getElementById('display');
        function press(val) { current += val; display.innerText = current; }
        function clearCalc() { current = ""; display.innerText = "0"; }
        function solve() { 
            try { 
                current = eval(current).toString(); 
                display.innerText = current; 
            } catch(e) { 
                display.innerText="Error"; 
                current=""; 
            } 
        }
        function sendResult() {
            try {
                let val = eval(current);
                if(!isNaN(val)) { 
                    window.parent.postMessage({type: "streamlit:setComponentValue", value: parseFloat(val)}, "*"); 
                }
            } catch(e) { console.error(e); }
        }
    </script>
    """
    return components.html(calc_html, height=400)

# 6. PANTALLA INGRESO (SOLUCIÓN AL ERROR DE SINCRONIZACIÓN)
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario")
    
    # Inicialización de estados
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    if 'show_calc' not in st.session_state: st.session_state.show_calc = False
    
    # Buffer de valor para desacoplar el iframe del widget nativo
    if 'temp_cant' not in st.session_state:
        st.session_state.temp_cant = 0.0

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res: return
    
    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    sel = st.selectbox("Selecciona producto:", [""] + sorted(list(prod_map.keys())))
    
    if sel:
        p = prod_map[sel]
        c1, c2, c3 = st.columns([2, 2, 0.6])
        
        with c1: 
            ubi = st.selectbox("Ubicación:", ["Bodega", "Frío", "Cocina", "Producción"])
        
        with c2:
            # El widget nativo ahora lee del buffer temp_cant
            # Usamos una key estática para evitar que se destruya el widget innecesariamente
            cant = st.number_input(
                "Cantidad:", 
                min_value=0.0, 
                value=float(st.session_state.temp_cant), 
                key="input_cantidad_fijo"
            )
            # Actualizamos el buffer con lo que el usuario escriba a mano
            st.session_state.temp_cant = cant

        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧮"): 
                st.session_state.show_calc = not st.session_state.show_calc
                st.rerun()

        # Lógica de la calculadora
        if st.session_state.show_calc:
            with st.expander("Calculadora", expanded=True):
                calc_val = calculadora_basica()
                # Solo procesamos si el componente envió un valor real (not None)
                if calc_val is not None:
                    st.session_state.temp_cant = float(calc_val)
                    st.session_state.show_calc = False
                    st.rerun()

        if st.button("Añadir a la lista"):
            st.session_state.carritos[user_key].append({
                "id_producto": p['id'], 
                "Producto": p['nombre'], 
                "Ubicación": ubi, 
                "Cantidad": float(st.session_state.temp_cant), 
                "Formato": p['formato_medida'], 
                "Factor": extraer_valor_formato(p['formato_medida'])
            })
            # Reset del buffer tras añadir
            st.session_state.temp_cant = 0.0
            st.rerun()

    # Mostrar tabla si hay items
    if st.session_state.carritos[user_key]:
        df_c = pd.DataFrame(st.session_state.carritos[user_key])
        ed = st.data_editor(df_c, column_config={"id_producto": None, "Factor": None}, use_container_width=True)
        
        if st.button("🚀 FINALIZAR"):
            for r in ed.to_dict(orient='records'):
                supabase.table("movimientos_inventario").insert({
                    "id_local": local_id, 
                    "id_producto": r['id_producto'], 
                    "cantidad": r['Cantidad']*r['Factor'], 
                    "tipo_movimiento": "AJUSTE", 
                    "ubicacion": r['Ubicación']
                }).execute()
            st.session_state.carritos[user_key] = []
            st.rerun()

# 7. REPORTES
def reportes_pantalla(local_id):
    st.header("📊 Reportes")
    query = supabase.table("movimientos_inventario").select("fecha_hora, tipo_movimiento, cantidad, ubicacion, productos_maestro(sku, nombre, formato_medida)").eq("id_local", local_id).execute().data
    if query:
        df = pd.json_normalize(query)
        st.dataframe(df, use_container_width=True)

# 8. MAESTRO
def admin_maestro(local_id):
    st.header("⚙️ Maestro")
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        df = pd.DataFrame(res)
        st.data_editor(df, use_container_width=True)

# 9. USUARIOS
def admin_usuarios(locales_map):
    st.header("👤 Usuarios")
    st.info("Gestión de usuarios activa.")

# 10. MAIN
def main():
    sync_session()
    if 'auth_user' not in st.session_state:
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Clave", type="password")
            if st.form_submit_button("Entrar"):
                if u=="admin" and p=="654321.": 
                    st.session_state.auth_user = {"user":"Admin", "role":"Admin", "local":1}
                    st.rerun()
        return

    user = st.session_state.auth_user
    if 'opt' not in st.session_state: 
        st.session_state.opt = "📋 Ingreso"
    
    st.sidebar.title("Menú")
    if st.sidebar.button("📋 Ingreso"): 
        st.session_state.opt = "📋 Ingreso"
        st.rerun()
    if st.sidebar.button("📊 Reportes"): 
        st.session_state.opt = "📊 Reportes"
        st.rerun()
    if user['role'] == "Admin":
        if st.sidebar.button("⚙️ Maestro"): 
            st.session_state.opt = "⚙️ Maestro"
            st.rerun()
    if st.sidebar.button("🚪 Salir"): 
        logout()

    if st.session_state.opt == "📋 Ingreso": 
        ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": 
        reportes_pantalla(user['local'])
    elif st.session_state.opt == "⚙️ Maestro": 
        admin_maestro(user['local'])

if __name__ == "__main__":
    main()
