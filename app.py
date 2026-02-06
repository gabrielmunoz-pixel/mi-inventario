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
    if "audit_list" in st.session_state:
        del st.session_state.audit_list
    st.query_params.clear()
    st.rerun()

# ==========================================
# 3. ESTILOS CSS
# ==========================================
st.markdown(f"""
    <style>
    .stApp {{ background-color: #000000; }}
    [data-testid="stSidebar"] {{ background-color: #111111; border-right: 1px solid #333; }}
    .stMarkdown p, label p, .stHeader h1, .stHeader h2, .stExpander p, .stAlert p {{ color: #FFFFFF !important; }}
    div.stButton > button {{ 
        background-color: #FFCC00 !important; color: #000000 !important; 
        font-weight: bold !important; border-radius: 10px !important; width: 100%;
    }}
    .nav-active > div > button {{ background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #FFCC00 !important; }}
    .red-btn > div > button {{ background-color: #DD0000 !important; color: white !important; }}
    .green-btn > div > button {{ background-color: #28a745 !important; color: white !important; }}
    .user-info {{ font-family: monospace; color: #FFCC00; font-size: 12px; margin-bottom: 10px; padding: 10px; border-bottom: 1px solid #333; }}
    iframe {{ max-width: 450px !important; display: block; margin: 0 auto; border: 1px solid #444; border-radius: 15px; background: #000; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. FUNCIONES DE APOYO
# ==========================================
def get_locales_map():
    try:
        res = supabase.table("locales").select("id, nombre").execute().data
        return {l['nombre']: l['id'] for l in res} if res else {}
    except: return {}

def extraer_valor_formato(formato_str):
    match = re.search(r"(\d+)", str(formato_str))
    return int(match.group(1)) if match else 1

def obtener_stock_dict(local_id):
    try:
        res = supabase.table("movimientos_inventario").select("id_producto, cantidad").eq("id_local", local_id).execute().data
        if not res: return {}
        df = pd.DataFrame(res)
        return df.groupby("id_producto")["cantidad"].sum().to_dict()
    except: return {}

# ==========================================
# 5. CALCULADORA (MEJORADA)
# ==========================================
def calculadora_basica():
    calc_html = """
    <div id="calc-container" style="background: #000; padding: 10px; border-radius: 15px; font-family: sans-serif;">
        <div id="display" style="background: #1e1e1e; color: #00ff00; padding: 15px; text-align: right; font-size: 28px; border-radius: 10px; margin-bottom: 15px; min-height: 40px; border: 2px solid #333; overflow-x: auto; white-space: nowrap; scrollbar-width: none;">0</div>
        
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
            <button onclick="press('7')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">7</button>
            <button onclick="press('8')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">8</button>
            <button onclick="press('9')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">9</button>
            <button onclick="press('/')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">/</button>
            
            <button onclick="press('4')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">4</button>
            <button onclick="press('5')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">5</button>
            <button onclick="press('6')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">6</button>
            <button onclick="press('*')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">*</button>
            
            <button onclick="press('1')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">1</button>
            <button onclick="press('2')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">2</button>
            <button onclick="press('3')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">3</button>
            <button onclick="press('-')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">-</button>
            
            <button onclick="press('0')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">0</button>
            <button onclick="press('.')" style="height: 45px; background: #FFCC00; border-radius: 8px; font-weight: bold;">.</button>
            <button onclick="solve()" style="height: 45px; background: #1A73E8; color: white; border-radius: 8px; font-weight: bold;">=</button>
            <button onclick="press('+')" style="height: 45px; background: #333; color: #FFCC00; border: 1px solid #FFCC00; border-radius: 8px;">+</button>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 15px;">
            <button onclick="clearCalc()" style="padding: 12px; background: #440000; color: white; border-radius: 8px; font-size: 12px;">C</button>
            <button onclick="backspace()" style="padding: 12px; background: #666; color: white; border-radius: 8px; font-size: 12px;">DEL</button>
            <button onclick="sendResult()" style="padding: 12px; background: #1A73E8; color: white; border-radius: 8px; font-weight: bold;">LISTO</button>
        </div>
    </div>
    <script>
        let current = "";
        const display = document.getElementById('display');

        function updateDisplay() {
            display.innerText = current || "0";
            display.scrollLeft = display.scrollWidth;
        }

        function press(val) { 
            current += val; 
            updateDisplay();
        }

        function clearCalc() { 
            current = ""; 
            updateDisplay();
        }

        function backspace() {
            current = current.toString().slice(0, -1);
            updateDisplay();
        }

        function solve() { 
            try { 
                if(current === "") return;
                current = eval(current).toString(); 
                updateDisplay();
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
            } catch(e) {}
        }
    </script>
    """
    return components.html(calc_html, height=400)

# ==========================================
# 6. PANTALLA: INGRESO
# ==========================================
def ingreso_inventario_pantalla(local_id, user_key):
    st.header("📋 Ingreso de Inventario")
    if 'carritos' not in st.session_state: st.session_state.carritos = {}
    if user_key not in st.session_state.carritos: st.session_state.carritos[user_key] = []
    if 'show_calc' not in st.session_state: st.session_state.show_calc = False
    # CAMBIO: Iniciamos en None para que el campo esté vacío
    if 'resultado_calc' not in st.session_state: st.session_state.resultado_calc = None

    res = supabase.table("productos_maestro").select("*").execute().data
    if not res:
        st.warning("No hay productos.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res}
    opciones = sorted(list(prod_map.keys()))
    sel = st.selectbox("Selecciona producto:", [""] + opciones)
    
    if sel:
        p = prod_map[sel]
        c1, c2, c3 = st.columns([2, 2, 0.6])
        with c1: ubi = st.selectbox("Ubicación:", ["Bodega", "Frío", "Cocina", "Producción"])
        with c2:
            placeholder_cant = st.empty()
            # CAMBIO: Si resultado_calc es None, pasamos None al value para limpiar el campo
            val_a_mostrar = float(st.session_state.resultado_calc) if st.session_state.resultado_calc is not None else None
            cant = placeholder_cant.number_input(
                "Cantidad:", 
                min_value=0.0, 
                value=val_a_mostrar,
                key=f"input_cant_{st.session_state.resultado_calc}"
            )
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🧮"): 
                st.session_state.show_calc = not st.session_state.show_calc
                st.rerun()

        if st.session_state.show_calc:
            with st.expander("Calculadora", expanded=True):
                calc_val = calculadora_basica()
                if calc_val is not None:
                    try:
                        st.session_state.resultado_calc = float(calc_val)
                        st.session_state.show_calc = False
                        st.rerun()
                    except: pass

        if st.button("Añadir a la lista"):
            if cant is not None and cant > 0:
                st.session_state.carritos[user_key].append({
                    "id_producto": p['id'], "Producto": p['nombre'], "Ubicación": ubi,
                    "Cantidad": float(cant), "Formato": p['formato_medida'], "Factor": extraer_valor_formato(p['formato_medida'])
                })
                st.toast("✅ Añadido")
                st.session_state.resultado_calc = None
                st.rerun()
            else:
                st.warning("Ingresa una cantidad válida.")

    if st.session_state.carritos[user_key]:
        st.subheader("🛒 Pre-ingreso")
        df_carrito = pd.DataFrame(st.session_state.carritos[user_key])
        ed = st.data_editor(df_carrito, column_config={"id_producto": None, "Factor": None}, use_container_width=True, key=f"ed_{user_key}")
        
        col_fin, col_del = st.columns(2)
        
        with col_fin:
            st.markdown('<div class="green-btn">', unsafe_allow_html=True)
            if 'confirm_guardar' not in st.session_state: st.session_state.confirm_guardar = False
            
            if not st.session_state.confirm_guardar:
                if st.button("🚀 FINALIZAR Y GUARDAR"):
                    st.session_state.confirm_guardar = True
                    st.rerun()
            else:
                st.warning("Confirmas que deseas ingresar las mercaderías?")
                c_si, c_no = st.columns(2)
                if c_si.button("✅ SÍ"):
                    for r in ed.to_dict(orient='records'):
                        supabase.table("movimientos_inventario").insert({
                            "id_local": local_id, "id_producto": r['id_producto'],
                            "cantidad": r['Cantidad'] * r['Factor'],
                            "tipo_movimiento": "AJUSTE", "ubicacion": r['Ubicación']
                        }).execute()
                    st.success("Guardado.")
                    st.session_state.carritos[user_key] = []
                    st.session_state.confirm_guardar = False
                    st.rerun()
                if c_no.button("❌ NO"):
                    st.session_state.confirm_guardar = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_del:
            st.markdown('<div class="red-btn">', unsafe_allow_html=True)
            if 'confirm_vaciar' not in st.session_state: st.session_state.confirm_vaciar = False
            
            if not st.session_state.confirm_vaciar:
                if st.button("🗑️ VACIAR"):
                    st.session_state.confirm_vaciar = True
                    st.rerun()
            else:
                st.error("¿Confirmas que deseas descartar el inventario?")
                v_si, v_no = st.columns(2)
                if v_si.button("🗑️ SÍ, VACIAR"):
                    st.session_state.carritos[user_key] = []
                    st.session_state.confirm_vaciar = False
                    st.rerun()
                if v_no.button("🔙 VOLVER"):
                    st.session_state.confirm_vaciar = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PANTALLA AUDITORÍA
# ==========================================
def auditoria_pantalla(local_id):
    st.header("🔎 Módulo de Auditoría")
    st.info("Este módulo es de comparación temporal. Los datos no se guardan en la DB.")
    
    if 'audit_list' not in st.session_state: st.session_state.audit_list = []
    
    stock_actual = obtener_stock_dict(local_id)
    res_prod = supabase.table("productos_maestro").select("*").execute().data
    
    if not res_prod:
        st.warning("No hay productos en el maestro.")
        return

    prod_map = {f"{p['nombre']} | {p['formato_medida']}": p for p in res_prod}
    
    with st.expander("➕ Añadir Producto a Revisión", expanded=True):
        sel = st.selectbox("Selecciona producto:", [""] + sorted(list(prod_map.keys())), key="audit_sel")
        if sel:
            p = prod_map[sel]
            factor = extraer_valor_formato(p['formato_medida'])
            stock_sistema = round(stock_actual.get(p['id'], 0) / factor, 2)
            
            c1, c2 = st.columns(2)
            cant_fisica = c1.number_input("Conteo Físico:", min_value=0.0, step=0.1)
            
            if c2.button("Registrar Comparación"):
                st.session_state.audit_list = [i for i in st.session_state.audit_list if i['id'] != p['id']]
                
                st.session_state.audit_list.append({
                    "id": p['id'],
                    "Producto": p['nombre'],
                    "Formato": p['formato_medida'],
                    "Sistema": stock_sistema,
                    "Físico": cant_fisica,
                    "Diferencia": round(cant_fisica - stock_sistema, 2)
                })
                st.rerun()

    if st.session_state.audit_list:
        st.subheader("📋 Lista de Comparación")
        df_audit = pd.DataFrame(st.session_state.audit_list)
        st.dataframe(df_audit.drop(columns=['id']), use_container_width=True, hide_index=True)
        
        col_acc1, col_acc2 = st.columns(2)
        if col_acc1.button("🗑️ Limpiar Lista"):
            st.session_state.audit_list = []
            st.rerun()
            
        csv = df_audit.to_csv(index=False).encode('utf-8')
        col_acc2.download_button("📥 Descargar Reporte (CSV)", csv, "auditoria.csv", "text/csv")

# ==========================================
# 7. PANTALLA: REPORTES
# ==========================================
def reportes_pantalla(local_id):
    st.header("📊 Reportes")
    t1, t2 = st.tabs(["🕒 Historial", "📦 Stock Actual"])
    try:
        query = supabase.table("movimientos_inventario").select("fecha_hora, tipo_movimiento, cantidad, ubicacion, productos_maestro(sku, nombre, formato_medida)").eq("id_local", local_id).execute().data
        if not query:
            st.info("No hay movimientos.")
            return
        df = pd.json_normalize(query)
        with t1:
            st.subheader("Historial")
            df_h = df[['fecha_hora', 'productos_maestro.sku', 'productos_maestro.nombre', 'tipo_movimiento', 'cantidad', 'ubicacion']].copy()
            st.dataframe(df_h, use_container_width=True)
        with t2:
            st.subheader("Stock Actual")
            df_s = df.groupby(['productos_maestro.sku', 'productos_maestro.nombre', 'productos_maestro.formato_medida'])['cantidad'].sum().reset_index()
            df_s['Factor'] = df_s['productos_maestro.formato_medida'].apply(extraer_valor_formato)
            df_s['Stock Neto'] = (df_s['cantidad'] / df_s['Factor']).round(2)
            st.dataframe(df_s[['productos_maestro.sku', 'productos_maestro.nombre', 'Stock Neto']], use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 8. PANTALLA: MAESTRO
# ==========================================
def admin_maestro(local_id):
    st.header("⚙️ Gestión de Maestro")
    with st.expander("📤 Importar Excel/CSV"):
        file = st.file_uploader("Archivo", type=["xlsx", "csv"])
        if file and st.button("Cargar"):
            try:
                df_up = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                mapeo = {"Número de artículo": "sku", "Descripción del artículo": "nombre", "Categoria": "categoria"}
                df_up = df_up.rename(columns=mapeo)
                if 'formato_medida' not in df_up.columns: df_up['formato_medida'] = "1 unidad"
                df_final = df_up[['sku', 'nombre', 'categoria', 'formato_medida']]
                supabase.table("productos_maestro").upsert(df_final.to_dict(orient='records'), on_conflict="sku").execute()
                st.success("Éxito.")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    res = supabase.table("productos_maestro").select("*").execute().data
    if res:
        st_dict = obtener_stock_dict(local_id)
        df_m = pd.DataFrame(res)
        df_m['Stock'] = df_m.apply(lambda r: round(st_dict.get(r['id'], 0) / extraer_valor_formato(r['formato_medida']), 2), axis=1)
        ed_m = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar Cambios"):
            for _, row in ed_m.iterrows():
                supabase.table("productos_maestro").upsert({"id": row['id'], "sku": row['sku'], "nombre": row['nombre'], "categoria": row['categoria'], "formato_medida": row['formato_medida']}).execute()
            st.success("Actualizado.")
            st.rerun()

# ==========================================
# 9. PANTALLA: USUARIOS
# ==========================================
def admin_usuarios(locales_map):
    st.header("👤 Gestión de Usuarios")
    if 'u_mode' not in st.session_state: st.session_state.u_mode = None
    c1, c2 = st.columns(2)
    if c1.button("➕ Nuevo Usuario"): st.session_state.u_mode = "Nuevo"
    if c2.button("✖️ Cerrar Formulario"): st.session_state.u_mode = None
    
    if st.session_state.u_mode:
        with st.form("user_new"):
            st.subheader("Crear Usuario")
            nombre = st.text_input("Nombre Completo")
            user_log = st.text_input("Usuario (Login)")
            pw = st.text_input("Contraseña", type="password")
            roles_asignados = st.multiselect("Asignar Perfiles:", ["Admin", "Staff", "Auditor"])
            l_sel = st.selectbox("Sede Asignada", list(locales_map.keys()))
            l_id = locales_map[l_sel]
            if st.form_submit_button("Registrar"):
                if nombre and user_log and pw and roles_asignados:
                    supabase.table("usuarios_sistema").upsert({
                        "nombre_apellido": nombre, "id_local": l_id, 
                        "usuario": user_log, "clave": pw, "rol": json.dumps(roles_asignados)
                    }, on_conflict="usuario").execute()
                    st.success("Registrado.")
                    st.session_state.u_mode = None
                    st.rerun()
                else: st.warning("Completa los campos.")

    st.markdown("---")
    try:
        res_u = supabase.table("usuarios_sistema").select("*").execute().data
        if res_u:
            df_users = pd.DataFrame(res_u)
            locales_inv = {v: k for k, v in locales_map.items()}
            df_users['Sede'] = df_users['id_local'].map(locales_inv)
            def clean_roles(r):
                try: return ", ".join(json.loads(r)) if "[" in r else r
                except: return r
            df_users['Perfiles'] = df_users['rol'].apply(clean_roles)
            st.dataframe(df_users[['nombre_apellido', 'usuario', 'Perfiles', 'Sede']], use_container_width=True)
    except: pass

# ==========================================
# 10. MAIN
# ==========================================
def main():
    sync_session()
    if 'auth_user' not in st.session_state:
        c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
        with c_l2:
            st.image("Logo AE.jpg", width=220)
            with st.form("Login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("ENTRAR"):
                    if u.lower() == "admin" and p == "654321.":
                        st.session_state.auth_user = {"user": "Master", "role": ["Admin"], "local": 1}
                        st.rerun()
                    res = supabase.table("usuarios_sistema").select("*").eq("usuario", u).eq("clave", p).execute().data
                    if res:
                        try: 
                            roles = json.loads(res[0]['rol'])
                            if not isinstance(roles, list): roles = [roles]
                        except: roles = [res[0]['rol']]
                        st.session_state.auth_user = {"user": res[0]['usuario'], "role": roles, "local": res[0]['id_local']}
                        st.rerun()
                    else: st.error("Error de login.")
        return

    user = st.session_state.auth_user
    locales = get_locales_map()
    locales_inv = {v: k for k, v in locales.items()}
    
    if "Admin" in user['role'] and locales:
        actual_name = locales_inv.get(user['local'], list(locales.keys())[0])
        idx = list(locales.keys()).index(actual_name)
        nueva_sede = st.sidebar.selectbox("Sede Activa:", list(locales.keys()), index=idx)
        user['local'] = locales[nueva_sede]
    
    st.sidebar.image("Logo AE.jpg", use_container_width=True)
    st.sidebar.markdown(f'<div class="user-info">👤 {user["user"]}<br>📍 {locales_inv.get(user["local"], "N/A")}</div>', unsafe_allow_html=True)
    
    menu_options = []
    if "Staff" in user['role'] or "Admin" in user['role']: menu_options.extend(["📋 Ingreso", "📊 Reportes"])
    if "Auditor" in user['role'] or "Admin" in user['role']: menu_options.append("🔎 Auditoría")
    if "Admin" in user['role']: menu_options.extend(["👤 Usuarios", "⚙️ Maestro"])
    
    menu = list(dict.fromkeys(menu_options))
    if 'opt' not in st.session_state or st.session_state.opt not in menu: st.session_state.opt = menu[0]
    
    for item in menu:
        estilo = "nav-active" if st.session_state.opt == item else ""
        st.sidebar.markdown(f'<div class="{estilo}">', unsafe_allow_html=True)
        if st.sidebar.button(item):
            st.session_state.opt = item
            st.rerun()
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    if st.sidebar.button("🚪 SALIR"): logout()
    
    if st.session_state.opt == "📋 Ingreso": ingreso_inventario_pantalla(user['local'], user['user'])
    elif st.session_state.opt == "📊 Reportes": reportes_pantalla(user['local'])
    elif st.session_state.opt == "🔎 Auditoría": auditoria_pantalla(user['local'])
    elif st.session_state.opt == "👤 Usuarios": admin_usuarios(locales)
    elif st.session_state.opt == "⚙️ Maestro": admin_maestro(user['local'])

if __name__ == "__main__":
    main()
