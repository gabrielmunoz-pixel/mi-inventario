import streamlit as st
import pandas as pd
import re
import json
from datetime import datetime
from supabase import create_client, Client
import streamlit.components.v1 as components

# --- 1. CONEXIÓN ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("Error de conexión con Supabase. Verifica los Secrets.")
    st.stop()

# --- 2. GESTIÓN DE SESIÓN ---
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

# --- 3. DISEÑO VISUAL ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}
    .stMarkdown p, label p, .stHeader h1, .stHeader h2, .stExpander p, .stAlert p {{ color: #FFFFFF !important; }}
    
    div.stButton > button {{ 
        background-color: #FFCC00 !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        border-radius: 10px !important;
        border: none !important;
    }}

    .nav-active > div > button {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FFCC00 !important;
    }}

    .red-btn > div > button {{
        background-color: #DD0000 !important;
        color: white !important;
    }}

    .green-btn > div > button {{
        background-color: #28a745 !important;
        color: white !important;
    }}

    .user-info {{
        font-family: monospace;
        color: #FFCC00;
        font-size: 12px;
        margin-bottom: 10px;
        padding: 5px;
        border-bottom: 1px solid #333;
    }}

    iframe {{
        max-width: 450px !important;
        display: block;
        margin: 0 auto;
        border: 1px solid #333;
        border-radius: 15px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNCIONES LÓGICAS ---
def get_locales_map():
    try:
        res = supabase.table("locales").select("id, nombre").execute().data
        if res:
            return {l['nombre']: l['id'] for l in res}
        return {}
    except:
        return {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    if match:
        return int(match.group(1))
    return 1

def obtener_stock_dict(local_id):
    try:
        res = supabase.table("movimientos_inventario").select("id_producto, cantidad").eq("id_local", local_id).execute().data
        if not res:
            return {}
        df = pd.DataFrame(res)
        stock_dict = df.groupby("id_producto")["cantidad"].sum().to_dict()
        return stock_dict
    except:
        return {}

# --- 5. COMPONENTE CALCULADORA ---
def calculadora_basica():
    # La lógica de JS ahora envía el mensaje correctamente al "padre" (Streamlit)
    calc_html = """
    <div id="calc-container" style="background: #000; padding: 10px; border-radius: 15px; font-family: sans-serif;">
        <div id="display" style="background: #1e1e1e; color: #00ff00; padding: 15px; text-align: right; font-size: 28px; border-radius: 10px; margin-bottom: 15px; min-height: 40px; border: 2px solid #333;">0</div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
            <button onclick="press('7')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">7</button>
            <button onclick="press('8')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">8</button>
            <button onclick="press('9')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">9</button>
            <button onclick="press('/')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px; font-size: 18px;">/</button>
            <button onclick="press('4')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">4</button>
            <button onclick="press('5')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">5</button>
            <button onclick="press('6')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">6</button>
            <button onclick="press('*')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px; font-size: 18px;">*</button>
            <button onclick="press('1')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">1</button>
            <button onclick="press('2')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">2</button>
            <button onclick="press('3')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">3</button>
            <button onclick="press('-')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px; font-size: 18px;">-</button>
            <button onclick="press('0')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">0</button>
            <button onclick="press('.')" style="height: 45px; background: #FFCC00; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">.</button>
            <button onclick="solve()" style="height: 45px; background: #1A73E8; color: white; border: none; border-radius: 8px; font-size: 18px; font-weight: bold;">=</button>
            <button onclick="press('+')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px; font-size: 18px;">+</button>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">
            <button onclick="clearCalc()" style="padding: 12px; background: #440000; color: white; border: none; border-radius: 8px; font-size: 14px;">Limpiar</button>
            <button onclick="sendResult()" style="padding: 12px; background: #1A73E8; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: bold;">LISTO</button>
        </div>
    </div>
    <script>
        let current = "";
        const display = document.getElementById('display');
        function press(val) { current += val; display.innerText = current; }
        function clearCalc() { current = ""; display.innerText = "0"; }
        function solve() {
            try {
                if (current === "") return;
                current = eval(current).toString();
                display.innerText = current;
            } catch (e) {
                display.innerText = "Error";
                current = "";
            }
        }
        function sendResult() {
            try {
                // Evaluamos por si el usuario no dio "=" antes de "LISTO"
                let finalVal = eval(current);
                // ESTA ES LA CLAVE: envía el valor al componente de Streamlit
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: finalVal
                }, "*");
            } catch (e) {
                console.error("Error al enviar dato");
            }
        }
    </script>
    """
    # Almacenamos lo que devuelve el iframe
    valor_devuelto = components.html(calc_html, height=400, scrolling=False)
    return valor_devuelto

# --- 6. PANTALLAS ---
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario")
    
    # Inicialización de estados
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    if 'show_calc' not in st.session_state: st.session_state.show_calc = False
    if 'resultado_calc' not in st.session_state: st.session_state.resultado_calc = 0.0

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("No hay productos disponibles.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    opciones = sorted(list(prod_map.keys()))
    
    sel = st.selectbox("Buscar producto:", [""] + opciones)
    
    if sel:
        p = prod_map[sel]
        c1, c2, c3 = st.columns([2, 2, 0.6])
        
        with c1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Frío", "Cocina", "Producción"])
        
        with c2:
            # EL TRUCO: El 'key' dinámico fuerza a Streamlit a actualizar el valor 
            # cuando resultado_calc cambia desde la calculadora.
            cant = st.number_input(
                "Cantidad:", 
                min_value=0.0, 
                step=1.0, 
                value=float(st.session_state.resultado_calc),
                key=f"input_cant_{st.session_state.resultado_calc}"
            )
            
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧮"):
                st.session_state.show_calc = not st.session_state.show_calc
                st.rerun()

        # Si la calculadora está abierta, capturamos su salida
        if st.session_state.show_calc:
            with st.expander("Calculadora de Cantidades", expanded=True):
                resultado_de_calculadora = calculadora_basica()
                
                # Si el componente envió un valor (al presionar LISTO)
                if resultado_de_calculadora is not None:
                    st.session_state.resultado_calc = float(resultado_de_calculadora)
                    st.session_state.show_calc = False # Cerramos calculadora
                    st.rerun() # Refrescamos para que el campo Cantidad tome el valor

        if st.button("Añadir a inventario"):
            st.session_state.carritos[user_key].append({
                "id_producto": p['id'],
                "Producto": p['nombre'],
                "Ubicación": ubi,
                "Cantidad": float(cant),
                "Formato": p['formato_medida'],
                "Factor": extraer_valor_formato(p['formato_medida'])
            })
            st.toast(f"✅ {p['nombre']} añadido")
            st.session_state.resultado_calc = 0.0 # Reseteamos para el siguiente producto
            st.rerun()

    if st.session_state.carritos[user_key]:
        st.subheader("🛒 Pre-ingreso Actual")
        df_carrito = pd.DataFrame(st.session_state.carritos[user_key])
        
        ed = st.data_editor(
            df_carrito,
            column_config={"id_producto": None, "Factor": None},
            use_container_width=True,
            key=f"editor_{user_key}"
        )

        col_c, col_a = st.columns(2)
        with col_c:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("🚀 FINALIZAR Y GUARDAR"):
                registros = ed.to_dict(orient='records')
                for r in registros:
                    supabase.table("movimientos_inventario").insert({
                        "id_local": local_id,
                        "id_producto": r['id_producto'],
                        "cantidad": r['Cantidad'] * r['Factor'],
                        "tipo_movimiento": "AJUSTE",
                        "ubicacion": r['Ubicación']
                    }).execute()
                st.success("¡Inventario guardado!")
                st.session_state.carritos[user_key] = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_a:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR TODO"):
                st.session_state.carritos[user_key] = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- LAS SIGUIENTES SECCIONES SON EL "ORIGINAL" SIN RECORTES ---

def reportes_pantalla(local_id):
    st.header("📊 Reportes de Inventario")
    t1, t2 = st.tabs(["🕒 Historial", "📦 Stock Actual"])
    try:
        query = supabase.table("movimientos_inventario").select("*, productos_maestro(sku, nombre, formato_medida)").eq("id_local", local_id).execute().data
        if not query:
            st.warning("Sin datos.")
            return
        df = pd.json_normalize(query)
        with t1:
            df_hist = df[['fecha_hora', 'productos_maestro.sku', 'productos_maestro.nombre', 'tipo_movimiento', 'cantidad', 'ubicacion']].copy()
            st.dataframe(df_hist, use_container_width=True)
        with t2:
            df_stock = df.groupby(['productos_maestro.sku', 'productos_maestro.nombre', 'productos_maestro.formato_medida'])['cantidad'].sum().reset_index()
            df_stock['Factor'] = df_stock['productos_maestro.formato_medida'].apply(extraer_valor_formato)
            df_stock['Stock Real'] = (df_stock['cantidad'] / df_stock['Factor']).round(2)
            st.dataframe(df_stock[['productos_maestro.sku', 'productos_maestro.nombre', 'Stock Real']], use_container_width=True)
    except Exception as e:
        st.error(f"Error en reportes: {e}")

def admin_maestro(local_id):
    st.header("⚙️ Maestro de Productos")
    with st.expander("📤 Carga Masiva (Excel / CSV)"):
        up = st.file_uploader("Subir archivo", type=["xlsx", "csv"])
        if up and st.button("Procesar y Cargar"):
            try:
                df_up = pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
                mapeo = {"Número de artículo": "sku", "Descripción del artículo": "nombre", "Categoria": "categoria"}
                df_up = df_up.rename(columns=mapeo)
                if 'formato_medida' not in df_up.columns: df_up['formato_medida'] = "1 unidad"
                df_final = df_up[[c for c in ['sku', 'nombre', 'categoria', 'formato_medida'] if c in df_up.columns]]
                supabase.table("productos_maestro").upsert(df_final.to_dict(orient='records'), on_conflict="sku").execute()
                st.success("✅ Cargado"); st.rerun()
            except Exception as e: st.error(str(e))

    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        st_dict = obtener_stock_dict(local_id)
        df_m = pd.DataFrame(res)
        df_m['Stock Actual'] = df_m.apply(lambda r: round(st_dict.get(r['id'], 0) / extraer_valor_formato(r['formato_medida']), 2), axis=1)
        ed = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar Cambios"):
            for i, row in ed.iterrows():
                supabase.table("productos_maestro").upsert({"id": row['id'], "sku": row['sku'], "nombre": row['nombre'], "categoria": row['categoria'], "formato_medida": row['formato_medida']}).execute()
            st.success("Actualizado"); st.rerun()

def admin_usuarios(locales_map):
    st.header("👤 Usuarios")
    if 'u_act' not in st.session_state: st.session_state.u_act = None
    c1, c2, c3 = st.columns(3)
    with c1: 
        if st.button("Nuevo Admin"): st.session_state.u_act = "admin"
    with c2: 
        if st.button("Nuevo Staff"): st.session_state.u_act = "staff"
    with c3: 
        if st.button("Cerrar"): st.session_state.u_act = None

    if st.session_state.u_act in ["admin", "staff"]:
        with st.form("form_u"):
            n = st.text_input("Nombre"); u = st.text_input("Usuario"); p = st.text_input("Clave", type="password")
            l_id = 1
            if st.session_state.u_act == "staff":
                l_sel = st.selectbox("Sede", list(locales_map.keys())); l_id = locales_map[l_sel]
            if st.form_submit_button("Crear"):
                rol = "Admin" if st.session_state.u_act == "admin" else "Staff"
                supabase.table("usuarios_sistema").upsert({"nombre_apellido": n, "id_local": l_id, "usuario": u, "clave": p, "rol": rol}, on_conflict="usuario").execute()
                st.success("Listo"); st.session_state.u_act = None; st.rerun()

def main():
    sync_session()
    if 'auth_user' not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login"):
                u = st.text_input("Usuario"); p = st.text_input("Clave", type="password")
                if st.form_submit_button("INGRESAR"):
                    if u.lower() == "admin" and p == "654321.":
                        st.session_state.auth_user = {"user": "Admin", "role": "Admin", "local": 1}; st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        st.session_state.auth_user = {"user": u, "role": res[0]['rol'], "local": res[0]['id_local']}; st.rerun()
                    else: st.error("Error de acceso.")
        return

    user = st.session_state.auth_user
    ld = get_locales_map()
    li = {v: k for k, v in ld.items()}
    if 'opt' not in st.session_state: st.session_state.opt = "📋 Ingreso"

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    if user['role'] == "Admin":
        actual_name = li.get(user['local'], list(ld.keys())[0] if ld else "")
        if ld:
            idx = list(ld.keys()).index(actual_name)
            nuevo_l = st.sidebar.selectbox("Sede:", list(ld.keys()), index=idx)
            user['local'] = ld[nuevo_l]

    st.sidebar.markdown(f'<div class="user-info">U: {user["user"]} | Sede: {li.get(user["local"], "N/A")}</div>', unsafe_allow_html=True)
    opts = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    
    for o in opts:
        estilo = "nav-active" if st.session_state.opt == o else ""
        st.sidebar.markdown(f'<div class="{estilo}">', unsafe_allow_html=True)
        if st.sidebar.button(o, key=f"sidebar_{o}"):
            st.session_state.opt = o; st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    if st.sidebar.button("🚪 Salir"): logout()

    if st.session_state.opt == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": reportes_pantalla(user['local'])
    elif st.session_state.opt == "👤 Usuarios": admin_usuarios(ld)
    elif st.session_state.opt == "⚙️ Maestro": admin_maestro(user['local'])

if __name__ == "__main__":
    main()
