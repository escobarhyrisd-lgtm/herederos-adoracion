import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from datetime import datetime, date
import uuid
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ─────────── Configuración de página ───────────
st.set_page_config(
    page_title="Herederos Adoración",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────── Estilos CSS ───────────
st.markdown("""
<style>
    body, .stApp { background-color: #0E1117; color: #E0E0E0; }
    .css-1d391kg, .css-1lcbmhc { background-color: #1A1C23; }
    .stButton>button {
        background-color: #D4AF37; color: #0E1117; font-weight: bold;
        border-radius: 8px; padding: 0.5rem 1rem;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        background-color: #E5C84A;
    }
    .stDownloadButton>button { background-color: #D4AF37; color: #0E1117; }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background-color: #262730; color: white;
        border-radius: 8px;
    }
    .st-bb { border-color: #D4AF37; }
    .stAlert { border-radius: 8px; }
    .css-1wrcr25 { background-color: #1A1C23; }
    
    /* Tarjetas */
    .card {
        background-color: #1A1C23;
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #D4AF37;
        margin-bottom: 1rem;
    }
    .card-title {
        color: #D4AF37;
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    @media (max-width: 768px) {
        .stApp { padding: 0.5rem; }
        .card { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ─────────── PWA ───────────
pwa_html = """
<link rel="manifest" href="/manifest.json">
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      navigator.serviceWorker.register('/sw.js')
        .then(function(registration) {
          console.log('ServiceWorker registrado:', registration.scope);
        })
        .catch(function(err) {
          console.log('Error ServiceWorker:', err);
        });
    });
  }
</script>
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# ─────────── Conexión a Supabase ───────────
SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("🔴 Configura las variables de entorno SUPABASE_URL y SUPABASE_KEY")
    st.stop()

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ─────────── Estado de sesión ───────────
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "rol" not in st.session_state:
    st.session_state.rol = None
if "perfil_id" not in st.session_state:
    st.session_state.perfil_id = None
if "nombre_usuario" not in st.session_state:
    st.session_state.nombre_usuario = None

# ─────────── Autenticación ───────────
def login():
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #D4AF37;">🎵 Herederos Adoración</h1>
        <p style="color: #888;">Sistema de gestión para el equipo de adoración</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🙌 Acceso al Equipo")
            email = st.text_input("📧 Correo electrónico", placeholder="tu@email.com")
            password = st.text_input("🔒 Contraseña", type="password", placeholder="••••••••")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Iniciar sesión", use_container_width=True):
                    if not email or not password:
                        st.error("Por favor, completa todos los campos")
                    else:
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            if res.user:
                                perfil = supabase.table("perfiles").select("*").eq("id", res.user.id).single().execute()
                                if perfil.data:
                                    st.session_state.usuario = res.user
                                    st.session_state.rol = perfil.data["rol"]
                                    st.session_state.perfil_id = perfil.data["id"]
                                    st.session_state.nombre_usuario = perfil.data["nombre"]
                                    st.success(f"✅ ¡Bienvenido, {perfil.data['nombre']}!")
                                    st.rerun()
                                else:
                                    st.error("Perfil no encontrado. Contacta al administrador.")
                                    supabase.auth.sign_out()
                            else:
                                st.error("❌ Credenciales inválidas")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            
            with col_btn2:
                if st.button("📝 Registrarse", use_container_width=True):
                    st.session_state.pagina_registro = True
                    st.rerun()

def registro():
    st.markdown("### 🎶 Únete al equipo de adoración")
    with st.form("registro", clear_on_submit=True):
        nombre = st.text_input("👤 Nombre completo")
        email = st.text_input("📧 Correo electrónico")
        telefono = st.text_input("📱 Teléfono")
        password = st.text_input("🔒 Contraseña", type="password")
        confirm_password = st.text_input("🔒 Confirmar contraseña", type="password")
        rol = st.selectbox("🎯 Tu rol principal", [
            "Músico", "Técnico de Sonido", "Técnico de Multimedia", "Adorador"
        ])
        sede = st.selectbox("📍 Sede", [
            "Tavacare", "Centro", "Toruno", "Barinitas", 
            "Guanapa", "Mi Jardín", "Quebrada Llena", "1ero de Diciembre"
        ])
        
        if st.form_submit_button("✅ Registrarme"):
            if password != confirm_password:
                st.error("Las contraseñas no coinciden")
                return
            if not nombre or not email or not password:
                st.error("Todos los campos son obligatorios")
                return
                
            try:
                # Verificar si el correo ya existe
                try:
                    supabase.auth.sign_in_with_password({"email": email, "password": " "})
                    st.error("Este correo ya está registrado. Inicia sesión.")
                    return
                except:
                    pass
                
                auth_res = supabase.auth.sign_up({"email": email, "password": password})
                if auth_res.user:
                    supabase.table("perfiles").upsert({
                        "id": auth_res.user.id,
                        "email": email,
                        "telefono": telefono,
                        "nombre": nombre,
                        "rol": rol,
                        "sede": sede
                    }).execute()
                    st.success("✅ Registro exitoso. El coordinador validará tu cuenta.")
                    st.session_state.pagina_registro = False
                    st.rerun()
            except Exception as e:
                st.error(f"Error en el registro: {str(e)}")
    
    if st.button("⬅ Volver al inicio de sesión"):
        st.session_state.pagina_registro = False
        st.rerun()

# ─────────── PÁGINAS ───────────

def pagina_canciones():
    st.markdown("### 🎼 Repositorio de Canciones")
    puede_gestionar = st.session_state.rol in ["Coordinador de Adoración", "Director de Alabanza"]
    
    if puede_gestionar:
        with st.expander("➕ Nueva canción", expanded=False):
            with st.form("nueva_cancion"):
                col1, col2 = st.columns(2)
                with col1:
                    titulo = st.text_input("Título*")
                    autor = st.text_input("Autor")
                    album = st.text_input("Álbum")
                    tonalidad = st.text_input("Tonalidad (ej. G)")
                with col2:
                    tempo = st.number_input("Tempo (BPM)", min_value=1, value=120)
                    duracion = st.number_input("Duración (segundos)", min_value=1, value=240)
                    version = st.text_input("Versión", "original")
                
                letra = st.text_area("📝 Letra completa", height=150)
                acordes = st.text_area("🎸 Acordes (progresión)", height=100)
                etiquetas = st.text_input("🏷️ Etiquetas (separadas por coma)")
                archivo = st.file_uploader("📄 Partitura (PDF/Imagen)", type=["pdf","png","jpg","jpeg"])
                
                if st.form_submit_button("💾 Guardar canción"):
                    if not titulo:
                        st.error("El título es obligatorio")
                    else:
                        ruta_partitura = None
                        if archivo:
                            try:
                                file_ext = archivo.name.split(".")[-1]
                                file_name = f"{uuid.uuid4()}.{file_ext}"
                                res_upload = supabase.storage.from_("partituras").upload(
                                    file_name, archivo.getvalue()
                                )
                                if res_upload:
                                    ruta_partitura = supabase.storage.from_("partituras").get_public_url(file_name)
                                    st.success("📄 Partitura subida correctamente")
                            except Exception as e:
                                st.error(f"Error al subir partitura: {str(e)}")
                                return
                        
                        etiq = [e.strip() for e in etiquetas.split(",")] if etiquetas else []
                        try:
                            supabase.table("canciones").insert({
                                "titulo": titulo,
                                "autor": autor,
                                "album": album,
                                "tonalidad": tonalidad,
                                "tempo": tempo,
                                "duracion": duracion,
                                "letra": letra,
                                "acordes": acordes,
                                "archivo_partitura": ruta_partitura,
                                "etiquetas": etiq,
                                "version": version
                            }).execute()
                            st.success("✅ Canción guardada correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {str(e)}")
    
    # Buscador
    busqueda = st.text_input("🔍 Buscar por título, autor, letra o etiqueta")
    
    try:
        canciones = supabase.table("canciones").select("*").order("titulo").execute()
        if canciones.data:
            df = pd.DataFrame(canciones.data)
            if busqueda:
                mask = df.apply(lambda row: busqueda.lower() in str(row).lower(), axis=1)
                df = df[mask]
            
            # Mostrar en tarjetas
            cols = st.columns(3)
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">{row['titulo']}</div>
                            <p style="color: #888; margin: 0;">✍️ {row.get('autor', 'Anónimo')}</p>
                            <p style="color: #666; font-size: 0.9rem;">🎵 {row.get('tonalidad', 'N/A')} • {row.get('tempo', '')} BPM</p>
                            <p style="color: #666; font-size: 0.9rem;">🏷️ {', '.join(row.get('etiquetas', [])) if row.get('etiquetas') else 'Sin etiquetas'}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Ver detalles
                        if st.button(f"📖 Ver detalles", key=f"ver_{row['id']}"):
                            st.session_state.cancion_detalle = row['id']
                            st.rerun()
            
            # Detalle de canción seleccionada
            if "cancion_detalle" in st.session_state:
                detalle = supabase.table("canciones").select("*").eq("id", st.session_state.cancion_detalle).single().execute()
                if detalle.data:
                    c = detalle.data
                    st.markdown("---")
                    st.markdown(f"## 🎵 {c['titulo']}")
                    if c['letra']:
                        st.markdown("### 📝 Letra")
                        st.text(c['letra'])
                    if c['acordes']:
                        st.markdown("### 🎸 Acordes")
                        st.text(c['acordes'])
                    if c['archivo_partitura']:
                        st.markdown(f"[📥 Descargar partitura]({c['archivo_partitura']})")
                    if st.button("❌ Cerrar detalles"):
                        del st.session_state.cancion_detalle
                        st.rerun()
# Editar canción (solo para coordinadores/directores)
if puede_gestionar:
    with st.expander("✏️ Editar canción"):
        with st.form("editar_cancion"):
            nuevo_titulo = st.text_input("Título", value=c.get('titulo', ''))
            nuevo_autor = st.text_input("Autor", value=c.get('autor', ''))
            nuevo_album = st.text_input("Álbum", value=c.get('album', ''))
            nueva_tonalidad = st.text_input("Tonalidad", value=c.get('tonalidad', ''))
            nuevo_tempo = st.number_input("Tempo (BPM)", value=c.get('tempo', 120))
            nueva_duracion = st.number_input("Duración (segundos)", value=c.get('duracion', 240))
            nueva_letra = st.text_area("Letra", value=c.get('letra', ''), height=200)
            nuevos_acordes = st.text_area("Acordes", value=c.get('acordes', ''), height=100)
            nuevas_etiquetas = st.text_input("Etiquetas", value=', '.join(c.get('etiquetas', [])) if c.get('etiquetas') else '')
            
            if st.form_submit_button("💾 Guardar cambios"):
                try:
                    supabase.table("canciones").update({
                        "titulo": nuevo_titulo,
                        "autor": nuevo_autor,
                        "album": nuevo_album,
                        "tonalidad": nueva_tonalidad,
                        "tempo": nuevo_tempo,
                        "duracion": nueva_duracion,
                        "letra": nueva_letra,
                        "acordes": nuevos_acordes,
                        "etiquetas": [e.strip() for e in nuevas_etiquetas.split(',')] if nuevas_etiquetas else []
                    }).eq("id", c['id']).execute()
                    st.success("✅ Canción actualizada correctamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar: {str(e)}")
        else:
            st.info("📭 No hay canciones aún. ¡Agrega la primera!")
    except Exception as e:
        st.error(f"Error al cargar canciones: {str(e)}")

def pagina_sets():
    st.markdown("### 📋 Planificación de Sets")
    puede_gestionar = st.session_state.rol in ["Coordinador de Adoración", "Director de Alabanza"]
    
    if puede_gestionar:
        with st.expander("🆕 Nuevo set", expanded=False):
            with st.form("nuevo_set"):
                col1, col2 = st.columns(2)
                with col1:
                    fecha = st.date_input("📅 Fecha")
                    servicio = st.selectbox("⛪ Servicio", ["Domingo", "Miércoles", "Viernes", "Sábado Juvenil"])
                with col2:
                    sede = st.selectbox("📍 Sede", ["Tavacare", "Centro", "Toruno", "Barinitas", "Guanapa", "Mi Jardín", "Quebrada Llena", "1ero de Diciembre"])
                    estado = st.selectbox("📊 Estado", ["Borrador", "Publicado"])
                
                notas = st.text_area("📝 Notas generales")
                
                if st.form_submit_button("✅ Crear set"):
                    try:
                        supabase.table("sets_adoracion").insert({
                            "fecha": str(fecha),
                            "servicio": servicio,
                            "sede": sede,
                            "estado": estado,
                            "notas": notas,
                            "created_by": st.session_state.perfil_id
                        }).execute()
                        st.success("✅ Set creado correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al crear set: {str(e)}")
    
    # Lista de sets
    try:
        sets = supabase.table("sets_adoracion").select("*").order("fecha", desc=True).execute()
        if sets.data:
            df_sets = pd.DataFrame(sets.data)
            
            # Mostrar en cards
            for _, row in df_sets.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">🎤 {row['servicio']}</div>
                            <p>📅 {row['fecha']} • 📍 {row['sede']}</p>
                            <p>📊 Estado: <strong>{row['estado']}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        # Ver canciones del set
                        if st.button(f"📋 Ver canciones", key=f"ver_set_{row['id']}"):
                            st.session_state.set_actual = row['id']
                            st.rerun()
                    with col3:
                        if puede_gestionar:
                            if st.button(f"🗑️", key=f"del_set_{row['id']}"):
                                try:
                                    supabase.table("sets_adoracion").delete().eq("id", row['id']).execute()
                                    st.success("Set eliminado")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
            
            # Detalle del set seleccionado
            if "set_actual" in st.session_state:
                set_id = st.session_state.set_actual
                st.markdown("---")
                st.markdown("### 🎵 Canciones del Set")
                
                canciones_set = supabase.table("set_canciones").select("*").eq("set_id", set_id).order("orden").execute()
                
                if canciones_set.data:
                    for c in canciones_set.data:
                        cancion = supabase.table("canciones").select("titulo").eq("id", c["cancion_id"]).single().execute()
                        if cancion.data:
                            cols = st.columns([3, 1])
                            with cols[0]:
                                st.write(f"**{c['orden']}.** {cancion.data['titulo']}")
                                if c.get('tonalidad_alternativa'):
                                    st.caption(f"Tonalidad: {c['tonalidad_alternativa']}")
                            with cols[1]:
                                if puede_gestionar:
                                    if st.button(f"🗑️", key=f"del_cancion_{c['id']}"):
                                        supabase.table("asignaciones").delete().eq("set_cancion_id", c["id"]).execute()
                                        supabase.table("set_canciones").delete().eq("id", c["id"]).execute()
                                        st.rerun()
                else:
                    st.info("No hay canciones en este set")
                
                # Agregar canción al set
                if puede_gestionar:
                    with st.expander("➕ Agregar canción al set"):
                        canciones_disp = supabase.table("canciones").select("id,titulo").execute()
                        if canciones_disp.data:
                            with st.form("agregar_cancion_set"):
                                cancion_id = st.selectbox(
                                    "Seleccionar canción",
                                    [c["id"] for c in canciones_disp.data],
                                    format_func=lambda x: next(c["titulo"] for c in canciones_disp.data if c["id"] == x)
                                )
                                orden = st.number_input("Orden", min_value=1, value=len(canciones_set.data)+1 if canciones_set.data else 1)
                                tonalidad_alt = st.text_input("Tonalidad alternativa")
                                notas_canc = st.text_area("Notas")
                                
                                if st.form_submit_button("Agregar"):
                                    try:
                                        supabase.table("set_canciones").insert({
                                            "set_id": set_id,
                                            "cancion_id": cancion_id,
                                            "orden": orden,
                                            "tonalidad_alternativa": tonalidad_alt,
                                            "notas_cancion": notas_canc
                                        }).execute()
                                        st.success("✅ Canción agregada")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                
                if st.button("❌ Cerrar set"):
                    del st.session_state.set_actual
                    st.rerun()
        else:
            st.info("📭 No hay sets planificados")
    except Exception as e:
        st.error(f"Error al cargar sets: {str(e)}")

def pagina_musicos():
    st.markdown("### 👥 Equipo de Músicos")
    puede_gestionar = st.session_state.rol in ["Coordinador de Adoración", "Director de Alabanza"]
    
    if puede_gestionar:
        with st.expander("➕ Registrar músico", expanded=False):
            with st.form("nuevo_musico"):
                email = st.text_input("📧 Correo del perfil")
                instrumentos = st.text_input("🎸 Instrumentos (separados por coma)")
                nivel = st.selectbox("📊 Nivel", ["principiante", "intermedio", "avanzado"])
                contacto = st.text_input("📱 Contacto")
                
                if st.form_submit_button("✅ Registrar"):
                    try:
                        perfil = supabase.table("perfiles").select("id").eq("email", email).single().execute()
                        if perfil.data:
                            supabase.table("musicos").insert({
                                "perfil_id": perfil.data["id"],
                                "instrumentos": [i.strip() for i in instrumentos.split(",")] if instrumentos else [],
                                "nivel": nivel,
                                "disponibilidad": "{}",
                                "contacto": contacto
                            }).execute()
                            st.success("✅ Músico registrado")
                            st.rerun()
                        else:
                            st.error("Perfil no encontrado")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # Lista de músicos
    try:
        musicos = supabase.table("musicos").select("*, perfiles(nombre, email)").execute()
        if musicos.data:
            for m in musicos.data:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">🎵 {m['perfiles']['nombre']}</div>
                            <p>📧 {m['perfiles']['email']}</p>
                            <p>🎸 {', '.join(m.get('instrumentos', [])) if m.get('instrumentos') else 'Sin instrumentos'}</p>
                            <p>📊 Nivel: {m.get('nivel', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("📭 No hay músicos registrados")
    except Exception as e:
        st.error(f"Error al cargar músicos: {str(e)}")

def pagina_tecnicos():
    st.markdown("### 🔧 Equipo Técnico")
    puede_gestionar = st.session_state.rol in ["Coordinador de Multimedia", "Coordinador de Adoración"]
    
    if puede_gestionar:
        with st.expander("➕ Nuevo técnico", expanded=False):
            with st.form("nuevo_tecnico"):
                email = st.text_input("📧 Correo del perfil")
                especialidad = st.multiselect(
                    "🔧 Especialidad",
                    ["sonido", "multimedia", "proyeccion", "camaras", "transmision"]
                )
                contacto = st.text_input("📱 Contacto")
                
                if st.form_submit_button("✅ Registrar"):
                    try:
                        perfil = supabase.table("perfiles").select("id").eq("email", email).single().execute()
                        if perfil.data:
                            supabase.table("tecnicos").insert({
                                "perfil_id": perfil.data["id"],
                                "especialidad": especialidad,
                                "disponibilidad": "{}",
                                "contacto": contacto
                            }).execute()
                            st.success("✅ Técnico registrado")
                            st.rerun()
                        else:
                            st.error("Perfil no encontrado")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # Lista de técnicos
    try:
        tecnicos = supabase.table("tecnicos").select("*, perfiles(nombre, email)").execute()
        if tecnicos.data:
            for t in tecnicos.data:
                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <div class="card-title">🔧 {t['perfiles']['nombre']}</div>
                        <p>📧 {t['perfiles']['email']}</p>
                        <p>🔧 {', '.join(t.get('especialidad', []))}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📭 No hay técnicos registrados")
    except Exception as e:
        st.error(f"Error al cargar técnicos: {str(e)}")

def pagina_recursos():
    st.markdown("### 🖼 Recursos Multimedia")
    
    if st.session_state.rol == "Coordinador de Multimedia":
        with st.expander("📤 Subir recurso", expanded=False):
            with st.form("nuevo_recurso"):
                nombre = st.text_input("📝 Nombre")
                tipo = st.selectbox("📁 Tipo", ["fondo", "loop", "plantilla", "grafico"])
                archivo = st.file_uploader("📄 Archivo", type=["jpg", "jpeg", "png", "mp4", "mp3", "wav"])
                etiquetas = st.text_input("🏷️ Etiquetas (separadas por coma)")
                
                if st.form_submit_button("📤 Subir"):
                    if archivo and nombre:
                        try:
                            file_name = f"{uuid.uuid4()}_{archivo.name}"
                            res = supabase.storage.from_("multimedia").upload(file_name, archivo.getvalue())
                            if res:
                                ruta = supabase.storage.from_("multimedia").get_public_url(file_name)
                                supabase.table("recursos_multimedia").insert({
                                    "nombre": nombre,
                                    "tipo": tipo,
                                    "archivo": ruta,
                                    "etiquetas": [e.strip() for e in etiquetas.split(",")] if etiquetas else []
                                }).execute()
                                st.success("✅ Recurso subido correctamente")
                                st.rerun()
                            else:
                                st.error("Error al subir el archivo")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    
    # Mostrar recursos
    try:
        recursos = supabase.table("recursos_multimedia").select("*").execute()
        if recursos.data:
            cols = st.columns(3)
            for idx, r in enumerate(recursos.data):
                with cols[idx % 3]:
                    with st.container():
                        if r["tipo"] in ["fondo", "grafico", "plantilla"]:
                            try:
                                st.image(r["archivo"], caption=r["nombre"], width=200)
                            except:
                                st.warning("No se puede mostrar la imagen")
                        else:
                            try:
                                st.audio(r["archivo"])
                            except:
                                st.warning("No se puede reproducir el audio")
                        st.caption(f"🏷️ {', '.join(r.get('etiquetas', [])) if r.get('etiquetas') else 'Sin etiquetas'}")
        else:
            st.info("📭 No hay recursos multimedia")
    except Exception as e:
        st.error(f"Error al cargar recursos: {str(e)}")

def pagina_calendario():
    st.markdown("### 📅 Calendario")
    
    try:
        sets = supabase.table("sets_adoracion").select("*").gte("fecha", str(date.today())).order("fecha").execute()
        
        st.subheader("🎯 Próximos servicios")
        if sets.data:
            for s in sets.data:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">🎤 {s['servicio']}</div>
                    <p>📅 {s['fecha']} • 📍 {s['sede']}</p>
                    <p>📊 Estado: <strong>{s['estado']}</strong></p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("📭 No hay servicios programados")
    except Exception as e:
        st.error(f"Error al cargar calendario: {str(e)}")

def pagina_chat():
    st.markdown("### 💬 Chat del Equipo")
    
    try:
        mensajes = supabase.table("chat_adoracion").select("*, perfiles(nombre)").order("created_at", desc=False).limit(50).execute()
        
        for msg in mensajes.data:
            with st.container():
                st.markdown(f"""
                <div style="background-color: #262730; border-radius: 8px; padding: 0.5rem 1rem; margin-bottom: 0.5rem;">
                    <strong style="color: #D4AF37;">{msg['perfiles']['nombre']}</strong>
                    <span style="color: #666; font-size: 0.8rem;">{msg['created_at']}</span>
                    <p style="margin: 0.2rem 0;">{msg['mensaje']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with st.form("mensaje"):
            texto = st.text_area("✏️ Escribe un mensaje", height=80)
            if st.form_submit_button("📤 Enviar"):
                if texto:
                    try:
                        supabase.table("chat_adoracion").insert({
                            "remitente_id": st.session_state.perfil_id,
                            "mensaje": texto
                        }).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al enviar: {str(e)}")
    except Exception as e:
        st.error(f"Error al cargar chat: {str(e)}")

def pagina_reportes():
    st.markdown("### 📊 Reportes")
    
    try:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_canciones = supabase.table("canciones").select("id", count="exact").execute().count
            st.metric("🎵 Canciones", total_canciones)
        
        with col2:
            total_sets = supabase.table("sets_adoracion").select("id", count="exact").execute().count
            st.metric("📋 Sets", total_sets)
        
        with col3:
            total_musicos = supabase.table("musicos").select("id", count="exact").execute().count
            st.metric("👥 Músicos", total_musicos)
        
        # Exportar datos
        st.subheader("📥 Exportar datos")
        sets = supabase.table("sets_adoracion").select("*").execute()
        if sets.data:
            csv = pd.DataFrame(sets.data).to_csv(index=False).encode('utf-8')
            st.download_button("📄 Descargar Sets (CSV)", csv, "sets.csv", "text/csv")
    except Exception as e:
        st.error(f"Error al cargar reportes: {str(e)}")

# ─────────── NAVEGACIÓN PRINCIPAL ───────────

def main():
    # Verificar estado de autenticación
    if not st.session_state.usuario:
        if st.session_state.get("pagina_registro"):
            registro()
        else:
            login()
        return
    
    # Sidebar con información del usuario
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #D4AF37;">🎵 HN</h2>
            <p style="color: #E0E0E0; font-weight: bold;">{st.session_state.nombre_usuario}</p>
            <p style="color: #888; font-size: 0.9rem;">{st.session_state.rol}</p>
            <p style="color: #666; font-size: 0.8rem;">{st.session_state.usuario.email}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Menú según rol
        menu_items = {
            "🎼 Canciones": pagina_canciones,
            "📋 Sets": pagina_sets,
        }
        
        if st.session_state.rol in ["Coordinador de Adoración", "Director de Alabanza", "Coordinador de Multimedia"]:
            menu_items["👥 Músicos"] = pagina_musicos
        
        if st.session_state.rol in ["Coordinador de Multimedia", "Coordinador de Adoración"]:
            menu_items["🔧 Técnicos"] = pagina_tecnicos
        
        if st.session_state.rol == "Coordinador de Multimedia":
            menu_items["🖼 Recursos"] = pagina_recursos
        
        menu_items["📅 Calendario"] = pagina_calendario
        menu_items["💬 Chat"] = pagina_chat
        menu_items["📊 Reportes"] = pagina_reportes
        
        opcion = st.radio("📌 Navegación", list(menu_items.keys()), label_visibility="collapsed")
        
        st.markdown("---")
        
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            try:
                supabase.auth.sign_out()
                for key in ["usuario", "rol", "perfil_id", "nombre_usuario"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            except Exception as e:
                st.error(f"Error al cerrar sesión: {str(e)}")
    
    # Renderizar página seleccionada
    menu_items[opcion]()

if __name__ == "__main__":
    main()
