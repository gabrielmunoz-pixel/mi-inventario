import streamlit as st
import pandas as pd
import re
import json
from datetime import datetime
from supabase import create_client, Client
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURACIÓN Y CONEXIÓN
# ==========================================
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Error de conexión con Supabase: {e}")
    st.stop()

# ==========================================
# 2. GESTIÓN DE SESIÓN Y AUTH
# ==========================================
def sync_session():
    """Sincroniza los datos del usuario con los parámetros de la URL para evitar cierres de sesión al refrescar."""
    params = st.query_params
    if "user_data" in params and "auth_user" not in st.session_state:
        try:
            st.session_state.auth_user = json.loads(params["user_data"])
        except:
            pass
    
    if "auth_user" in st.session_state:
        st.query_params["user_data"] = json.dumps(st.session_state.auth_user)

def logout():
    """Limpia la sesión y reinicia la app."""
    if "auth_user" in st.session_state:
        del st.session_state.auth_user
    if "carritos" in st.session_state:
        st.session_state.carritos = {}
    st.query_params.clear()
    st.rerun()

# ==========================================
# 3. ESTILOS CSS (DISEÑO MODO OSCURO)
# ==========================================
st.markdown(f"""
    <style>
    /* Fondo General */
    .stApp {{
        background-color: #000000;
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: #111111;
        border-right: 1px solid #333;
    }}
    
    /* Textos */
    .stMarkdown p, label p, .stHeader h1, .stHeader h2, .stExpander p, .stAlert p {{
        color: #FFFFFF !important;
    }}
    
    /* Botones Estándar (Amarillos) */
    div.stButton > button {{ 
        background-color: #FFCC00 !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        border-radius: 10px !important;
        border: none !important;
        width: 100%;
    }}

    /* Botón Activo en Sidebar */
    .nav-active > div > button {{
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FFCC00 !important;
    }}

    /* Botones Especiales */
    .red-btn > div > button {{
        background-color: #DD0000 !important;
        color: white !important;
    }}

    .green-btn > div > button {{
        background-color: #28a745 !important;
        color: white !important;
    }}

    /* Info de Usuario */
    .user-info {{
        font-family: monospace;
        color: #FFCC00;
        font-size: 12px;
        margin-bottom: 10px;
        padding: 10px;
        border-bottom: 1px solid #333;
    }}

    /* Calculadora Iframe */
    iframe {{
        max-width: 450px !important;
        display: block;
        margin: 0 auto;
        border: 1px solid #444;
        border-radius: 15px;
        background: #000;
    }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. FUNCIONES DE APOYO (LÓGICA)
# ==========================================
def get_locales_map():
    """Obtiene el mapa de nombres e IDs de locales."""
    try:
        res = supabase.table("locales").select("id, nombre").execute().data
        if res:
            return {l['nombre']: l['id'] for l in res}
        return {}
    except Exception:
        return {}

def extraer_valor_formato(formato_str):
    """Extrae el número de un string como 'Pack 24' -> 24."""
    match = re.search(r"(\d+)", str(formato_str))
    if match:
        return int(match.group(1))
    return 1

def obtener_stock_dict(local_id):
    """Calcula el stock actual agrupado por producto para un local."""
    try:
        res = supabase.table("movimientos_inventario").select("id_producto, cantidad").eq("id_local", local_id).execute().data
        if not res:
            return {}
        df = pd.DataFrame(res)
        return df.groupby("id_producto")["cantidad"].sum().to_dict()
    except Exception:
        return {}

# ==========================================
# 5. COMPONENTE CALCULADORA (HTML/JS)
# ==========================================
def calculadora_basica():
    """Renderiza la calculadora y gestiona el envío de datos a Streamlit."""
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
                let val = eval(current);
                window.parent.postMessage({type: "streamlit:setComponentValue", value: val}, "*");
            } catch (e) {}
        }
    </script>
    """
    return components.html(calc_html, height=400, scrolling=False)

# ==========================================
# 6. PANTALLA: INGRESO DE INVENTARIO
# ==========================================
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario")
    
    # Inicializar estados de esta pantalla
    if 'carritos' not in st.session_state:
        st.session_state.carritos = {}
    if user_key not in st.session_state.carritos:
        st.session_state.carritos[user_key] = []
    
    if 'show_calc' not in st.session_state:
        st.session_state.show_calc = False
    if 'resultado_calc' not in st.session_state:
        st.session_state.resultado_calc = 0.0

    # Cargar maestro
    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("No hay productos en el sistema.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    opciones = sorted(list(prod_map.keys()))
    
    sel = st.selectbox("Selecciona producto:", [""] + opciones)
    
    if sel:
        p = prod_map[sel]
        c1, c2, c3 = st.columns([2, 2, 0.6])
        
        with c1:
            ubi = st.selectbox("Ubicación:", ["Bodega", "Frío", "Cocina", "Producción"])
        
        with c2:
            cant = st.number_input(
                "Cantidad:", 
                min_value=0.0, 
                step=1.0, 
                value=float(st.session_state.resultado_calc),
                key=f"input_cant_{st.session_state.resultado_calc}"
            )
            
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧮", help="Abrir calculadora"):
                st.session_state.show_calc = not st.session_state.show_calc
                st.rerun()

        # Render de Calculadora si está activa
        if st.session_state.show_calc:
            with st.expander("Calculadora", expanded=True):
                calc_val = calculadora_basica()
                # CORRECCIÓN DEL TypeError: Verificar que no sea None antes de convertir
                if calc_val is not None:
                    try:
                        st.session_state.resultado_calc = float(calc_val)
                        st.session_state.show_calc = False
                        st.rerun()
                    except (TypeError, ValueError):
                        pass

        if st.button("Añadir a la lista"):
            st.session_state.carritos[user_key].append({
                "id_producto": p['id'],
                "Producto": p['nombre'],
                "Ubicación": ubi,
                "Cantidad": float(cant),
                "Formato": p['formato_medida'],
                "Factor": extraer_valor_formato(p['formato_medida'])
            })
            st.toast(f"✅ {p['nombre']} añadido")
            st.session_state.resultado_calc = 0.0
            st.rerun()

    # Tabla de Pre-ingreso
    if st.session_state.carritos[user_key]:
        st.subheader("🛒 Pre-ingreso")
        df_carrito = pd.DataFrame(st.session_state.carritos[user_key])
        
        ed = st.data_editor(
            df_carrito,
            column_config={"id_producto": None, "Factor": None},
            use_container_width=True,
            key=f"ed_{user_key}"
        )

        col_fin, col_del = st.columns(2)
        with col_fin:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if st.button("🚀 FINALIZAR Y GUARDAR"):
                for r in ed.to_dict(orient='records'):
                    supabase.table("movimientos_inventario").insert({
                        "id_local": local_id,
                        "id_producto": r['id_producto'],
                        "cantidad": r['Cantidad'] * r['Factor'],
                        "tipo_movimiento": "AJUSTE",
                        "ubicacion": r['Ubicación']
                    }).execute()
                st.success("Guardado correctamente.")
                st.session_state.carritos[user_key] = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_del:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if st.button("🗑️ VACIAR LISTA"):
                st.session_state.carritos[user_key] = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. PANTALLA: REPORTES
# ==========================================
def reportes_pantalla(local_id):
    st.header("📊 Reportes")
    t1, t2 = st.tabs(["🕒 Historial", "📦 Stock Actual"])
    
    try:
        query = supabase.table("movimientos_inventario").select(
            "fecha_hora, tipo_movimiento, cantidad, ubicacion, productos_maestro(sku, nombre, formato_medida)"
        ).eq("id_local", local_id).execute().data
        
        if not query:
            st.info("No hay movimientos registrados.")
            return

        df = pd.json_normalize(query)
        
        with t1:
            st.subheader("Historial de Movimientos")
            df_h = df[['fecha_hora', 'productos_maestro.sku', 'productos_maestro.nombre', 'tipo_movimiento', 'cantidad', 'ubicacion']].copy()
            st.dataframe(df_h, use_container_width=True)
            
        with t2:
            st.subheader("Estado de Stock")
            df_s = df.groupby(['productos_maestro.sku', 'productos_maestro.nombre', 'productos_maestro.formato_medida'])['cantidad'].sum().reset_index()
            df_s['Factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
            df_s['Stock Neto'] = (df_s['cantidad'] / df_s['Factor']).round(2)
            st.dataframe(df_s[['productos_maestro.sku', 'productos_maestro.nombre', 'Stock Neto']], use_container_width=True)
            
    except Exception as e:
        st.error(f"Error cargando reportes: {e}")

# ==========================================
# 8. PANTALLA: MAESTRO DE PRODUCTOS
# ==========================================
def admin_maestro(local_id):
    st.header("⚙️ Gestión de Maestro")
    
    with st.expander("📤 Importar desde Excel/CSV"):
        file = st.file_uploader("Archivo", type=["xlsx", "csv"])
        if file and st.button("Cargar Archivo"):
            try:
                df_up = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                mapeo = {"Número de artículo": "sku", "Descripción del artículo": "nombre", "Categoria": "categoria"}
                df_up = df_up.rename(columns=mapeo)
                if 'formato_medida' not in df_up.columns:
                    df_up['formato_medida'] = "1 unidad"
                
                cols = ['sku', 'nombre', 'categoria', 'formato_medida']
                df_final = df_up[[c for c in cols if c in df_up.columns]]
                
                supabase.table("productos_maestro").upsert(df_final.to_dict(orient='records'), on_conflict="sku").execute()
                st.success("Carga masiva finalizada.")
                st.rerun()
            except Exception as e:
                st.error(f"Error en carga: {e}")

    # Editar Tabla Maestro
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        st.subheader("Productos Registrados")
        st_dict = obtener_stock_dict(local_id)
        df_m = pd.DataFrame(res)
        df_m['Stock'] = df_m.apply(lambda r: round(st_dict.get(r['id'], 0) / extraer_valor_formato(r['formato_medida']), 2), axis=1)
        
        ed_m = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Guardar Cambios en Maestro"):
            for _, row in ed_m.iterrows():
                supabase.table("productos_maestro").upsert({
                    "id": row['id'],
                    "sku": row['sku'],
                    "nombre": row['nombre'],
                    "categoria": row['categoria'],
                    "formato_medida": row['formato_medida']
                }).execute()
            st.success("Maestro actualizado.")
            st.rerun()

# ==========================================
# 9. PANTALLA: GESTIÓN DE USUARIOS
# ==========================================
def admin_usuarios(locales_map):
    st.header("👤 Usuarios y Permisos")
    
    if 'u_mode' not in st.session_state:
        st.session_state.u_mode = None

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("➕ Nuevo Admin"): st.session_state.u_mode = "Admin"
    with c2:
        if st.button("➕ Nuevo Staff"): st.session_state.u_mode = "Staff"
    with c3:
        if st.button("✖️ Cerrar"): st.session_state.u_mode = None

    if st.session_state.u_mode:
        with st.form("user_new"):
            st.write(f"Registro de {st.session_state.u_mode}")
            nombre = st.text_input("Nombre Completo")
            user_log = st.text_input("ID Usuario (Login)")
            password = st.text_input("Contraseña", type="password")
            
            l_id = 1
            if st.session_state.u_mode == "Staff":
                l_sel = st.selectbox("Sede Asignada", list(locales_map.keys()))
                l_id = locales_map[l_sel]
                
            if st.form_submit_button("Registrar Usuario"):
                supabase.table("usuarios_sistema").upsert({
                    "nombre_apellido": nombre,
                    "id_local": l_id,
                    "usuario": user_log,
                    "clave": password,
                    "rol": st.session_state.u_mode
                }, on_conflict="usuario").execute()
                st.success("Usuario registrado.")
                st.session_state.u_mode = None
                st.rerun()

# ==========================================
# 10. FUNCIÓN PRINCIPAL (ORQUESTADOR)
# ==========================================
def main():
    sync_session()

    # --- LOGIN ---
    if 'auth_user' not in st.session_state:
        c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
        with c_l2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login_AE"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("ENTRAR AL SISTEMA"):
                    if u.lower() == "admin" and p == "654321.":
                        st.session_state.auth_user = {"user": "Master", "role": "Admin", "local": 1}
                        st.rerun()
                    
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        st.session_state.auth_user = {
                            "user": res[0]['usuario'],
                            "role": res[0]['rol'],
                            "local": res[0]['id_local']
                        }
                        st.rerun()
                    else:
                        st.error("Usuario o clave incorrectos.")
        return

    # --- PANEL DE CONTROL ---
    user = st.session_state.auth_user
    locales = get_locales_map()
    locales_inv = {v: k for k, v in locales.items()}

    if 'opt' not in st.session_state:
        st.session_state.opt = "📋 Ingreso"

    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    
    if user['role'] == "Admin":
        actual_name = locales_inv.get(user['local'], list(locales.keys())[0] if locales else "Sede")
        if locales:
            idx = list(locales.keys()).index(actual_name)
            nueva_sede = st.sidebar.selectbox("Cambiar Sede:", list(locales.keys()), index=idx)
            user['local'] = locales[nueva_sede]

    st.sidebar.markdown(f'<div class="user-info">👤 {user["user"]}<br>📍 {locales_inv.get(user["local"], "N/A")}</div>', unsafe_allow_html=True)
    
    menu = ["📋 Ingreso", "📊 Reportes", "👤 Usuarios", "⚙️ Maestro"] if user['role'] == "Admin" else ["📋 Ingreso", "📊 Reportes"]
    
    for item in menu:
        estilo = "nav-active" if st.session_state.opt == item else ""
        st.sidebar.markdown(f'<div class="{estilo}">', unsafe_allow_html=True)
        if st.sidebar.button(item, key=f"m_{item}"):
            st.session_state.opt = item
            st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    if st.sidebar.button("🚪 SALIR"):
        logout()

    # --- RUTEADOR DE PANTALLAS ---
    if st.session_state.opt == "📋 Ingreso":
        ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes":
        reportes_pantalla(user['local'])
    elif st.session_state.opt == "👤 Usuarios":
        admin_usuarios(locales)
    elif st.session_state.opt == "⚙️ Maestro":
        admin_maestro(user['local'])

if __name__ == "__main__":
    main()
