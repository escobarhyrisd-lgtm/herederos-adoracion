import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from datetime import datetime, date
import uuid
import re
from io import BytesIO
from fpdf import FPDF

# ─────────── Utilidades de transposición de acordes ───────────
NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ENARMONICOS = {"Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B", "E#": "F", "B#": "C"}
PATRON_ACORDE = re.compile(r'([A-G](?:#|b)?)((?:maj|min|dim|aug|sus|add)?[0-9]*m?[0-9]*)(?:/([A-G](?:#|b)?))?')

def _transponer_nota(nota, semitonos):
    nota_norm = ENARMONICOS.get(nota, nota)
    if nota_norm not in NOTAS:
        return nota
    idx = NOTAS.index(nota_norm)
    return NOTAS[(idx + semitonos) % 12]

def transponer_acordes(texto, semitonos):
    """Transpone acordes en notación estándar (G, Am7, D/F#, etc). No es infalible con notaciones complejas."""
    if not texto or not semitonos:
        return texto
    def _reemplazar(match):
        raiz, calidad, bajo = match.groups()
        resultado = _transponer_nota(raiz, semitonos) + (calidad or "")
        if bajo:
            resultado += "/" + _transponer_nota(bajo, semitonos)
        return resultado
    return PATRON_ACORDE.sub(_reemplazar, texto)

# ─────────── Configuración de página y tema ───────────
st.set_page_config(
    page_title="Herederos Adoración",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
                enlace_referencia = st.text_input("🎧 Enlace de pista de referencia (Spotify, YouTube, etc.)")
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
                                "version": version,
                                "enlace_referencia": enlace_referencia or None
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
                        
                        if st.button(f"📖 Ver detalles", key=f"ver_{row['id']}"):
                            mostrar_detalle_cancion(row['id'], puede_gestionar)
        else:
            st.info("📭 No hay canciones aún. ¡Agrega la primera!")
    except Exception as e:
        st.error(f"Error al cargar canciones: {str(e)}")

@st.dialog("🎵 Detalle de la canción", width="large")
def mostrar_detalle_cancion(cancion_id, puede_gestionar):
    detalle = supabase.table("canciones").select("*").eq("id", cancion_id).single().execute()
    if detalle.data:
        c = detalle.data
        st.markdown(f"## {c['titulo']}")
        st.caption(f"✍️ {c.get('autor', 'Anónimo')} · 🎵 {c.get('tonalidad', 'N/A')} · {c.get('tempo', '')} BPM")
        if c.get('enlace_referencia'):
            st.markdown(f"[🎧 Escuchar pista de referencia]({c['enlace_referencia']})")
        if c.get('letra'):
            st.markdown("### 📝 Letra")
            st.text(c['letra'])
        if c.get('acordes'):
            semitonos = st.slider("🎼 Transponer (semitonos)", -6, 6, 0, key=f"transp_detalle_{c['id']}")
            tonalidad_mostrada = transponer_acordes(c.get('tonalidad', ''), semitonos) if semitonos else c.get('tonalidad', '')
            st.markdown(f"### 🎸 Acordes {f'· Tonalidad: {tonalidad_mostrada}' if tonalidad_mostrada else ''}")
            st.text(transponer_acordes(c['acordes'], semitonos) if semitonos else c['acordes'])
        if c.get('archivo_partitura'):
            st.markdown(f"[📥 Descargar partitura]({c['archivo_partitura']})")

        if puede_gestionar:
            with st.expander("✏️ Editar canción", expanded=False):
                with st.form("editar_cancion"):
                    nuevo_titulo = st.text_input("Título", value=c.get('titulo', ''))
                    nuevo_autor = st.text_input("Autor", value=c.get('autor', ''))
                    nuevo_album = st.text_input("Álbum", value=c.get('album', ''))
                    nueva_tonalidad = st.text_input("Tonalidad", value=c.get('tonalidad', ''))
                    nuevo_tempo = st.number_input("Tempo (BPM)", value=c.get('tempo', 120))
                    nueva_duracion = st.number_input("Duración (segundos)", value=c.get('duracion', 240))
                    nueva_letra = st.text_area("Letra", value=c.get('letra', ''), height=200)
                    nuevos_acordes = st.text_area("Acordes", value=c.get('acordes', ''), height=100)
                    nuevas_etiquetas = st.text_input("Etiquetas (separadas por coma)", value=', '.join(c.get('etiquetas', [])) if c.get('etiquetas') else '')
                    nuevo_enlace = st.text_input("Enlace de pista de referencia", value=c.get('enlace_referencia', '') or '')

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
                                "etiquetas": [e.strip() for e in nuevas_etiquetas.split(',')] if nuevas_etiquetas else [],
                                "enlace_referencia": nuevo_enlace or None
                            }).eq("id", c['id']).execute()
                            st.success("✅ Canción actualizada correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")



@st.dialog("🎤 Modo Servicio", width="large")
def mostrar_modo_servicio():
    set_id = st.session_state.modo_servicio_set
    canciones_set = supabase.table("set_canciones").select(
        "*, canciones(titulo, tonalidad, letra, acordes, enlace_referencia)"
    ).eq("set_id", set_id).order("orden").execute()
    items = canciones_set.data or []

    if not items:
        st.info("Este set no tiene canciones todavía")
        if st.button("Cerrar"):
            del st.session_state.modo_servicio_set
            del st.session_state.modo_servicio_idx
            st.rerun()
        return

    idx = max(0, min(st.session_state.modo_servicio_idx, len(items) - 1))
    item = items[idx]
    c = item.get("canciones") or {}
    tonalidad_original = item.get("tonalidad_alternativa") or c.get("tonalidad") or "—"

    st.markdown(f"**Canción {idx + 1} de {len(items)}**")
    st.markdown(f"## {c.get('titulo', '—')}")
    if item.get("notas_cancion"):
        st.info(f"📌 {item['notas_cancion']}")
    if c.get("enlace_referencia"):
        st.markdown(f"[🎧 Escuchar pista de referencia]({c['enlace_referencia']})")

    key_transp = f"transp_{item['id']}"
    if key_transp not in st.session_state:
        st.session_state[key_transp] = 0
    semitonos = st.slider("🎼 Transponer tonalidad (semitonos)", -6, 6, st.session_state[key_transp], key=f"slider_{item['id']}")
    st.session_state[key_transp] = semitonos
    tonalidad_transpuesta = transponer_acordes(tonalidad_original, semitonos) if tonalidad_original != "—" else "—"
    etiqueta_ton = f"**{tonalidad_transpuesta}**" + (f" _(original {tonalidad_original})_" if semitonos else "")
    st.caption(f"Tonalidad: {etiqueta_ton}")

    tab_letra, tab_acordes = st.tabs(["📝 Letra", "🎸 Acordes"])
    with tab_letra:
        texto = c.get("letra") or "Sin letra registrada"
        st.markdown(
            f"<div style='font-size:1.5rem; line-height:2.1rem; white-space:pre-wrap;'>{texto}</div>",
            unsafe_allow_html=True
        )
    with tab_acordes:
        acordes_mostrados = transponer_acordes(c.get("acordes") or "", semitonos) if semitonos else (c.get("acordes") or "")
        st.code(acordes_mostrados or "Sin acordes registrados")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅ Anterior", disabled=(idx == 0), use_container_width=True):
            st.session_state.modo_servicio_idx -= 1
            st.rerun()
    with col2:
        if st.button("❌ Cerrar", use_container_width=True):
            del st.session_state.modo_servicio_set
            del st.session_state.modo_servicio_idx
            st.rerun()
    with col3:
        if st.button("Siguiente ➡", disabled=(idx == len(items) - 1), use_container_width=True):
            st.session_state.modo_servicio_idx += 1
            st.rerun()


def _pdf_texto_seguro(texto):
    """fpdf2 con fuente base solo soporta latin-1; sustituye lo que no entra."""
    if not texto:
        return ""
    return texto.encode("latin-1", "replace").decode("latin-1")


def generar_pdf_set(set_id):
    try:
        set_info = supabase.table("sets_adoracion").select("*").eq("id", set_id).single().execute().data
        canciones_set = supabase.table("set_canciones").select(
            "*, canciones(titulo, tonalidad, letra, acordes)"
        ).eq("set_id", set_id).order("orden").execute().data

        if not set_info:
            return None, "No se encontró el set"

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, _pdf_texto_seguro(f"Orden de servicio - {set_info['servicio']}"), ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, _pdf_texto_seguro(f"Fecha: {set_info['fecha']}  |  Sede: {set_info['sede']}"), ln=True)
        if set_info.get("notas"):
            pdf.multi_cell(0, 6, _pdf_texto_seguro(f"Notas: {set_info['notas']}"))
        pdf.ln(4)

        for item in (canciones_set or []):
            c = item.get("canciones") or {}
            tonalidad = item.get("tonalidad_alternativa") or c.get("tonalidad") or "-"

            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 8, _pdf_texto_seguro(f"{item['orden']}. {c.get('titulo', '-')}  (Tonalidad: {tonalidad})"))

            # Personas asignadas
            asign = supabase.table("asignaciones").select(
                "*, perfiles(nombre)"
            ).eq("set_cancion_id", item["id"]).execute().data
            if asign:
                pdf.set_font("Helvetica", "I", 10)
                nombres = "; ".join(
                    f"{a['perfiles']['nombre']} ({a['tipo_rol']})" for a in asign if a.get("perfiles")
                )
                pdf.multi_cell(0, 6, _pdf_texto_seguro(f"Equipo: {nombres}"))

            if item.get("notas_cancion"):
                pdf.set_font("Helvetica", "I", 10)
                pdf.multi_cell(0, 6, _pdf_texto_seguro(f"Nota: {item['notas_cancion']}"))

            if c.get("letra"):
                pdf.set_font("Helvetica", "", 10)
                # multi_cell puede fallar con palabras/lineas muy largas sin espacios (ej. URLs pegadas);
                # se procesa línea por línea para aislar el problema a esa línea puntual
                for linea in c["letra"].split("\n"):
                    try:
                        pdf.multi_cell(0, 5, _pdf_texto_seguro(linea))
                    except Exception:
                        pdf.multi_cell(0, 5, _pdf_texto_seguro(linea[:80]))

            pdf.ln(4)

        return bytes(pdf.output()), None
    except Exception as e:
        return None, str(e)


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
            
            for _, row in df_sets.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 1.3, 1.3, 0.6])
                    with col1:
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">🎤 {row['servicio']}</div>
                            <p>📅 {row['fecha']} • 📍 {row['sede']}</p>
                            <p>📊 Estado: <strong>{row['estado']}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        if st.button(f"📋 Ver canciones", key=f"ver_set_{row['id']}"):
                            st.session_state.set_actual = row['id']
                            st.rerun()
                        if st.button("▶️ Modo Servicio", key=f"modo_servicio_{row['id']}"):
                            st.session_state.modo_servicio_set = row['id']
                            st.session_state.modo_servicio_idx = 0
                            st.rerun()
                    with col3:
                        pdf_bytes, pdf_error = generar_pdf_set(row['id'])
                        if pdf_bytes:
                            st.download_button(
                                "📥 Orden de servicio (PDF)", pdf_bytes,
                                file_name=f"orden_servicio_{row['fecha']}.pdf",
                                mime="application/pdf",
                                key=f"pdf_set_{row['id']}"
                            )
                        elif pdf_error:
                            st.caption(f"⚠️ No se pudo generar el PDF: {pdf_error}")
                    with col4:
                        if puede_gestionar:
                            if st.button("✏️", key=f"editar_set_{row['id']}"):
                                st.session_state[f"editando_set_{row['id']}"] = not st.session_state.get(f"editando_set_{row['id']}", False)
                                st.rerun()
                            if st.button(f"🗑️", key=f"del_set_{row['id']}"):
                                try:
                                    supabase.table("sets_adoracion").delete().eq("id", row['id']).execute()
                                    st.success("Set eliminado")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

                    if puede_gestionar and st.session_state.get(f"editando_set_{row['id']}"):
                        with st.form(f"form_editar_set_{row['id']}"):
                            st.markdown(f"**✏️ Editando set: {row['servicio']} ({row['fecha']})**")
                            ecol1, ecol2 = st.columns(2)
                            with ecol1:
                                nueva_fecha = st.date_input("📅 Fecha", value=pd.to_datetime(row['fecha']).date(), key=f"efecha_{row['id']}")
                                nuevo_servicio = st.selectbox(
                                    "⛪ Servicio", ["Domingo", "Miércoles", "Viernes", "Sábado Juvenil"],
                                    index=["Domingo", "Miércoles", "Viernes", "Sábado Juvenil"].index(row['servicio']) if row['servicio'] in ["Domingo", "Miércoles", "Viernes", "Sábado Juvenil"] else 0,
                                    key=f"eservicio_{row['id']}"
                                )
                            with ecol2:
                                sedes_lista = ["Tavacare", "Centro", "Toruno", "Barinitas", "Guanapa", "Mi Jardín", "Quebrada Llena", "1ero de Diciembre"]
                                nueva_sede = st.selectbox("📍 Sede", sedes_lista, index=sedes_lista.index(row['sede']) if row['sede'] in sedes_lista else 0, key=f"esede_{row['id']}")
                                nuevo_estado = st.selectbox("📊 Estado", ["Borrador", "Publicado"], index=["Borrador", "Publicado"].index(row['estado']) if row['estado'] in ["Borrador", "Publicado"] else 0, key=f"eestado_{row['id']}")
                            nuevas_notas = st.text_area("📝 Notas generales", value=row.get('notas', '') or '', key=f"enotas_{row['id']}")

                            gcol1, gcol2 = st.columns(2)
                            with gcol1:
                                if st.form_submit_button("💾 Guardar cambios"):
                                    supabase.table("sets_adoracion").update({
                                        "fecha": str(nueva_fecha),
                                        "servicio": nuevo_servicio,
                                        "sede": nueva_sede,
                                        "estado": nuevo_estado,
                                        "notas": nuevas_notas
                                    }).eq("id", row['id']).execute()
                                    st.session_state[f"editando_set_{row['id']}"] = False
                                    st.success("✅ Set actualizado")
                                    st.rerun()
                            with gcol2:
                                if st.form_submit_button("Cancelar"):
                                    st.session_state[f"editando_set_{row['id']}"] = False
                                    st.rerun()

            if st.session_state.get("modo_servicio_set"):
                mostrar_modo_servicio()

            
            if "set_actual" in st.session_state:
                set_id = st.session_state.set_actual
                set_info_actual = supabase.table("sets_adoracion").select("servicio,fecha").eq("id", set_id).single().execute().data or {}
                servicio_actual = set_info_actual.get("servicio")
                fecha_actual = set_info_actual.get("fecha")
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

                            # ─── Personas asignadas y su estado de confirmación ───
                            asign = supabase.table("asignaciones").select(
                                "*, perfiles(nombre)"
                            ).eq("set_cancion_id", c["id"]).execute()
                            if asign.data:
                                badge = {
                                    "Confirmado": "🟢 Confirmado",
                                    "Rechazado": "🔴 Rechazado",
                                    "Pendiente": "🟡 Pendiente"
                                }
                                for a in asign.data:
                                    estado_a = a.get("estado_confirmacion", "Pendiente")
                                    nombre_p = a["perfiles"]["nombre"] if a.get("perfiles") else "—"
                                    st.caption(f"　↳ {nombre_p} · {a['tipo_rol']} · {badge.get(estado_a, estado_a)}")
                else:
                    st.info("No hay canciones en este set")
                
                # AGREGAR CANCIÓN AL SET
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
                
                # ASIGNAR PERSONA A CANCIÓN (ACCESO PARA COORDINADOR DE ADORACIÓN)
                if st.session_state.rol in ["Coordinador de Adoración", "Coordinador de Multimedia", "Director de Alabanza"]:
                    st.markdown("---")
                    st.subheader("👤 Asignar persona a canción")
                    if canciones_set.data:
                        cancion_set_id = st.selectbox(
                            "Seleccionar canción del set",
                            [c["id"] for c in canciones_set.data],
                            format_func=lambda x: f"Orden {next(c['orden'] for c in canciones_set.data if c['id']==x)}"
                        )
                        if cancion_set_id:
                            personas = supabase.table("perfiles").select("id,nombre,rol").execute().data
                            musicos_disp = {m["perfil_id"]: m for m in (supabase.table("musicos").select("perfil_id,dias_disponibles,fechas_no_disponible").execute().data or [])}
                            tecnicos_disp = {t["perfil_id"]: t for t in (supabase.table("tecnicos").select("perfil_id,dias_disponibles,fechas_no_disponible").execute().data or [])}

                            def _etiqueta_persona(p):
                                ficha = musicos_disp.get(p["id"]) or tecnicos_disp.get(p["id"])
                                if ficha is None:
                                    return f"{p['nombre']} ({p['rol']})"
                                dias = ficha.get("dias_disponibles") or []
                                fechas_bloq = ficha.get("fechas_no_disponible") or []
                                if fecha_actual and str(fecha_actual) in fechas_bloq:
                                    return f"🔴 {p['nombre']} ({p['rol']}) · NO disponible el {fecha_actual}"
                                if servicio_actual and servicio_actual in dias:
                                    return f"🟢 {p['nombre']} ({p['rol']}) · disponible {servicio_actual}"
                                elif dias:
                                    return f"🟡 {p['nombre']} ({p['rol']}) · disponible: {', '.join(dias)}"
                                else:
                                    return f"⚪ {p['nombre']} ({p['rol']}) · sin días definidos"

                            ops = {p["id"]: _etiqueta_persona(p) for p in personas}
                            persona_id = st.selectbox("Persona", list(ops.keys()), format_func=lambda x: ops[x])
                            tipo_rol = st.selectbox("Rol", [
                                "vocalista_principal","corista","piano","guitarra","bajo",
                                "bateria","teclado","violin","saxofon","sonido",
                                "proyeccion","camaras","transmision"
                            ])
                            if st.button("✅ Asignar"):
                                try:
                                    supabase.table("asignaciones").insert({
                                        "set_cancion_id": cancion_set_id,
                                        "persona_id": persona_id,
                                        "tipo_rol": tipo_rol
                                    }).execute()
                                    st.success("✅ Persona asignada correctamente")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al asignar: {str(e)}")
                
                if st.button("❌ Cerrar set"):
                    del st.session_state.set_actual
                    st.rerun()
        else:
            st.info("📭 No hay sets planificados")
    except Exception as e:
        st.error(f"Error al cargar sets: {str(e)}")

DIAS_SERVICIO = ["Domingo", "Miércoles", "Viernes", "Sábado Juvenil"]

def pagina_musicos():
    st.markdown("### 👥 Equipo de Músicos")
    puede_gestionar = st.session_state.rol in ["Coordinador de Adoración", "Director de Alabanza"]
    
    if puede_gestionar:
        with st.expander("➕ Registrar músico", expanded=False):
            with st.form("nuevo_musico"):
                email = st.text_input("📧 Correo del perfil")
                instrumentos = st.text_input("🎸 Instrumentos (separados por coma)")
                nivel = st.selectbox("📊 Nivel", ["principiante", "intermedio", "avanzado"])
                dias = st.multiselect("📅 Días disponibles", DIAS_SERVICIO)
                contacto = st.text_input("📱 Contacto")
                
                if st.form_submit_button("✅ Registrar"):
                    try:
                        perfil = supabase.table("perfiles").select("id").eq("email", email).single().execute()
                        if perfil.data:
                            supabase.table("musicos").insert({
                                "perfil_id": perfil.data["id"],
                                "instrumentos": [i.strip() for i in instrumentos.split(",")] if instrumentos else [],
                                "nivel": nivel,
                                "dias_disponibles": dias,
                                "disponibilidad": "{}",
                                "contacto": contacto
                            }).execute()
                            st.success("✅ Músico registrado")
                            st.rerun()
                        else:
                            st.error("Perfil no encontrado")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    try:
        musicos = supabase.table("musicos").select("*, perfiles(nombre, email)").execute()
        if musicos.data:
            for m in musicos.data:
                with st.container():
                    es_propio = m.get("perfil_id") == st.session_state.perfil_id
                    st.markdown(f"""
                    <div class="card">
                        <div class="card-title">🎵 {m['perfiles']['nombre']}</div>
                        <p>📧 {m['perfiles']['email']}</p>
                        <p>🎸 {', '.join(m.get('instrumentos', [])) if m.get('instrumentos') else 'Sin instrumentos'}</p>
                        <p>📊 Nivel: {m.get('nivel', 'N/A')}</p>
                        <p>📅 Disponible: {', '.join(m.get('dias_disponibles', [])) if m.get('dias_disponibles') else 'Sin definir'}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if es_propio or puede_gestionar:
                        with st.expander(f"✏️ Editar disponibilidad de {m['perfiles']['nombre']}"):
                            with st.form(f"editar_disp_musico_{m['id']}"):
                                nuevos_dias = st.multiselect(
                                    "Días disponibles", DIAS_SERVICIO,
                                    default=m.get("dias_disponibles", [])
                                )
                                if st.form_submit_button("💾 Guardar"):
                                    supabase.table("musicos").update({
                                        "dias_disponibles": nuevos_dias
                                    }).eq("id", m["id"]).execute()
                                    st.success("✅ Disponibilidad actualizada")
                                    st.rerun()

                            st.markdown("**🚫 Fechas puntuales no disponible** (ej. vacaciones, viajes)")
                            fechas_bloqueadas = m.get("fechas_no_disponible") or []
                            if fechas_bloqueadas:
                                for fb in sorted(fechas_bloqueadas):
                                    cfb1, cfb2 = st.columns([3, 1])
                                    cfb1.caption(f"📅 {fb}")
                                    if cfb2.button("✖", key=f"quitar_fecha_musico_{m['id']}_{fb}"):
                                        supabase.table("musicos").update({
                                            "fechas_no_disponible": [f for f in fechas_bloqueadas if f != fb]
                                        }).eq("id", m["id"]).execute()
                                        st.rerun()
                            nueva_fecha = st.date_input("Agregar fecha no disponible", key=f"nueva_fecha_musico_{m['id']}")
                            if st.button("➕ Agregar fecha", key=f"add_fecha_musico_{m['id']}"):
                                fechas_actualizadas = list(set(fechas_bloqueadas + [str(nueva_fecha)]))
                                supabase.table("musicos").update({
                                    "fechas_no_disponible": fechas_actualizadas
                                }).eq("id", m["id"]).execute()
                                st.rerun()
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
                dias = st.multiselect("📅 Días disponibles", DIAS_SERVICIO)
                contacto = st.text_input("📱 Contacto")
                
                if st.form_submit_button("✅ Registrar"):
                    try:
                        perfil = supabase.table("perfiles").select("id").eq("email", email).single().execute()
                        if perfil.data:
                            supabase.table("tecnicos").insert({
                                "perfil_id": perfil.data["id"],
                                "especialidad": especialidad,
                                "dias_disponibles": dias,
                                "disponibilidad": "{}",
                                "contacto": contacto
                            }).execute()
                            st.success("✅ Técnico registrado")
                            st.rerun()
                        else:
                            st.error("Perfil no encontrado")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    try:
        tecnicos = supabase.table("tecnicos").select("*, perfiles(nombre, email)").execute()
        if tecnicos.data:
            for t in tecnicos.data:
                with st.container():
                    es_propio = t.get("perfil_id") == st.session_state.perfil_id
                    st.markdown(f"""
                    <div class="card">
                        <div class="card-title">🔧 {t['perfiles']['nombre']}</div>
                        <p>📧 {t['perfiles']['email']}</p>
                        <p>🔧 {', '.join(t.get('especialidad', []))}</p>
                        <p>📅 Disponible: {', '.join(t.get('dias_disponibles', [])) if t.get('dias_disponibles') else 'Sin definir'}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if es_propio or puede_gestionar:
                        with st.expander(f"✏️ Editar disponibilidad de {t['perfiles']['nombre']}"):
                            with st.form(f"editar_disp_tecnico_{t['id']}"):
                                nuevos_dias = st.multiselect(
                                    "Días disponibles", DIAS_SERVICIO,
                                    default=t.get("dias_disponibles", [])
                                )
                                if st.form_submit_button("💾 Guardar"):
                                    supabase.table("tecnicos").update({
                                        "dias_disponibles": nuevos_dias
                                    }).eq("id", t["id"]).execute()
                                    st.success("✅ Disponibilidad actualizada")
                                    st.rerun()

                            st.markdown("**🚫 Fechas puntuales no disponible** (ej. vacaciones, viajes)")
                            fechas_bloqueadas = t.get("fechas_no_disponible") or []
                            if fechas_bloqueadas:
                                for fb in sorted(fechas_bloqueadas):
                                    cfb1, cfb2 = st.columns([3, 1])
                                    cfb1.caption(f"📅 {fb}")
                                    if cfb2.button("✖", key=f"quitar_fecha_tecnico_{t['id']}_{fb}"):
                                        supabase.table("tecnicos").update({
                                            "fechas_no_disponible": [f for f in fechas_bloqueadas if f != fb]
                                        }).eq("id", t["id"]).execute()
                                        st.rerun()
                            nueva_fecha = st.date_input("Agregar fecha no disponible", key=f"nueva_fecha_tecnico_{t['id']}")
                            if st.button("➕ Agregar fecha", key=f"add_fecha_tecnico_{t['id']}"):
                                fechas_actualizadas = list(set(fechas_bloqueadas + [str(nueva_fecha)]))
                                supabase.table("tecnicos").update({
                                    "fechas_no_disponible": fechas_actualizadas
                                }).eq("id", t["id"]).execute()
                                st.rerun()
        else:
            st.info("📭 No hay técnicos registrados")
    except Exception as e:
        st.error(f"Error al cargar técnicos: {str(e)}")

def pagina_recursos():
    st.markdown("### 🖼 Recursos Multimedia")
    
    # COORDINADOR DE ADORACIÓN Y MULTIMEDIA PUEDEN SUBIR RECURSOS
    if st.session_state.rol in ["Coordinador de Multimedia", "Coordinador de Adoración"]:
        with st.expander("📤 Subir recurso", expanded=False):
            with st.form("nuevo_recurso"):
                nombre = st.text_input("📝 Nombre")
                tipo = st.selectbox("📁 Tipo", ["fondo", "loop", "plantilla", "grafico"])
                archivo = st.file_uploader("📄 Archivo", type=["jpg", "jpeg", "png", "mp4", "mp3", "wav"])
                etiquetas = st.text_input("🏷️ Etiquetas (separadas por coma)")
                sets_disp = supabase.table("sets_adoracion").select("id,servicio,fecha").order("fecha", desc=True).execute().data or []
                set_opciones = {**{None: "— Ninguno —"}, **{s["id"]: f"{s['servicio']} ({s['fecha']})" for s in sets_disp}}
                set_vinculado = st.selectbox("🎤 Vincular a un set (opcional)", list(set_opciones.keys()), format_func=lambda x: set_opciones[x])
                
                if st.form_submit_button("📤 Subir"):
                    if archivo and nombre:
                        try:
                            file_name = f"{uuid.uuid4()}_{archivo.name}"
                            res = supabase.storage.from_("multimedia").upload(file_name, archivo.getvalue())
                            if res:
                                ruta = supabase.storage.from_("multimedia").get_public_url(file_name)
                                nuevo_recurso = supabase.table("recursos_multimedia").insert({
                                    "nombre": nombre,
                                    "tipo": tipo,
                                    "archivo": ruta,
                                    "etiquetas": [e.strip() for e in etiquetas.split(",")] if etiquetas else []
                                }).execute()
                                if set_vinculado and nuevo_recurso.data:
                                    supabase.table("asignaciones_recursos").insert({
                                        "set_id": set_vinculado,
                                        "recurso_id": nuevo_recurso.data[0]["id"]
                                    }).execute()
                                st.success("✅ Recurso subido correctamente")
                                st.rerun()
                            else:
                                st.error("Error al subir el archivo")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
    
    try:
        recursos = supabase.table("recursos_multimedia").select("*").execute()
        if recursos.data:
            vinculos = supabase.table("asignaciones_recursos").select(
                "recurso_id, sets_adoracion(servicio, fecha)"
            ).execute().data or []
            vinculos_por_recurso = {}
            for v in vinculos:
                s = v.get("sets_adoracion") or {}
                if s:
                    vinculos_por_recurso.setdefault(v["recurso_id"], []).append(f"{s['servicio']} ({s['fecha']})")

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
                        sets_vinculados = vinculos_por_recurso.get(r["id"])
                        if sets_vinculados:
                            st.caption(f"🎤 Vinculado a: {', '.join(sets_vinculados)}")
        else:
            st.info("📭 No hay recursos multimedia")
    except Exception as e:
        st.error(f"Error al cargar recursos: {str(e)}")

def pagina_mis_asignaciones():
    st.markdown("### ✅ Mis Servicios")
    st.caption("Confirma o rechaza tu participación en los próximos servicios")

    try:
        mias = supabase.table("asignaciones").select(
            "*, set_canciones(orden, tonalidad_alternativa, sets_adoracion(id, fecha, servicio, sede), canciones(titulo))"
        ).eq("persona_id", st.session_state.perfil_id).execute()

        if not mias.data:
            st.info("📭 No tienes asignaciones registradas todavía")
            return

        # Agrupar por set (servicio)
        por_set = {}
        for a in mias.data:
            sc = a.get("set_canciones") or {}
            set_info = sc.get("sets_adoracion") or {}
            set_id = set_info.get("id", "sin_set")
            por_set.setdefault(set_id, {"info": set_info, "items": []})
            por_set[set_id]["items"].append(a)

        badge = {"Confirmado": "🟢 Confirmado", "Rechazado": "🔴 Rechazado", "Pendiente": "🟡 Pendiente"}

        for set_id, grupo in sorted(
            por_set.items(),
            key=lambda kv: kv[1]["info"].get("fecha") or "",
            reverse=True
        ):
            info = grupo["info"]
            st.markdown(f"""
            <div class="card">
                <div class="card-title">🎤 {info.get('servicio', 'Servicio')}</div>
                <p>📅 {info.get('fecha', '—')} • 📍 {info.get('sede', '—')}</p>
            </div>
            """, unsafe_allow_html=True)

            for a in grupo["items"]:
                sc = a.get("set_canciones") or {}
                titulo_cancion = (sc.get("canciones") or {}).get("titulo", "—")
                estado_a = a.get("estado_confirmacion", "Pendiente")

                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                with col1:
                    st.write(f"🎵 {titulo_cancion} · {a['tipo_rol']}")
                with col2:
                    st.caption(badge.get(estado_a, estado_a))
                with col3:
                    if st.button("✅", key=f"confirmar_{a['id']}", help="Confirmar"):
                        supabase.table("asignaciones").update({
                            "estado_confirmacion": "Confirmado",
                            "fecha_respuesta": datetime.now().isoformat()
                        }).eq("id", a["id"]).execute()
                        st.rerun()
                with col4:
                    if st.button("❌", key=f"rechazar_{a['id']}", help="No podré asistir"):
                        st.session_state[f"rechazar_nota_{a['id']}"] = True
                        st.rerun()

                if st.session_state.get(f"rechazar_nota_{a['id']}"):
                    with st.form(f"form_rechazo_{a['id']}"):
                        nota = st.text_input("Motivo (opcional)")
                        if st.form_submit_button("Confirmar rechazo"):
                            supabase.table("asignaciones").update({
                                "estado_confirmacion": "Rechazado",
                                "fecha_respuesta": datetime.now().isoformat(),
                                "nota_respuesta": nota
                            }).eq("id", a["id"]).execute()
                            del st.session_state[f"rechazar_nota_{a['id']}"]
                            st.rerun()

            st.markdown("---")
    except Exception as e:
        st.error(f"Error al cargar tus asignaciones: {str(e)}")

def pagina_ensayos():
    st.markdown("### 🎯 Ensayos")
    puede_gestionar = st.session_state.rol in ["Coordinador de Adoración", "Director de Alabanza"]

    if puede_gestionar:
        with st.expander("🆕 Programar ensayo", expanded=False):
            with st.form("nuevo_ensayo"):
                col1, col2 = st.columns(2)
                with col1:
                    fecha_hora = st.date_input("📅 Fecha")
                    hora = st.time_input("🕒 Hora")
                    lugar = st.text_input("📍 Lugar (ej. Salón de ensayos)")
                with col2:
                    sede = st.selectbox("⛪ Sede", [
                        "Tavacare", "Centro", "Toruno", "Barinitas",
                        "Guanapa", "Mi Jardín", "Quebrada Llena", "1ero de Diciembre"
                    ])
                    sets_disp = supabase.table("sets_adoracion").select("id,servicio,fecha").order("fecha", desc=True).execute().data or []
                    set_opciones = {**{None: "— Ninguno —"}, **{s["id"]: f"{s['servicio']} ({s['fecha']})" for s in sets_disp}}
                    set_id = st.selectbox("Vincular a un set (opcional)", list(set_opciones.keys()), format_func=lambda x: set_opciones[x])

                notas = st.text_area("📝 Notas del ensayo")
                personas = supabase.table("perfiles").select("id,nombre,rol").execute().data or []
                participantes = st.multiselect(
                    "👥 Participantes",
                    [p["id"] for p in personas],
                    format_func=lambda x: next((f"{p['nombre']} ({p['rol']})" for p in personas if p["id"] == x), x)
                )

                if st.form_submit_button("✅ Programar ensayo"):
                    try:
                        supabase.table("ensayos").insert({
                            "set_id": set_id,
                            "fecha_hora": datetime.combine(fecha_hora, hora).isoformat(),
                            "lugar": lugar,
                            "sede": sede,
                            "notas": notas,
                            "participantes": participantes
                        }).execute()
                        st.success("✅ Ensayo programado correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al programar el ensayo: {str(e)}")

    try:
        ensayos = supabase.table("ensayos").select("*, sets_adoracion(servicio, fecha)").order("fecha_hora", desc=True).execute()
        if ensayos.data:
            personas_map = {p["id"]: p["nombre"] for p in (supabase.table("perfiles").select("id,nombre").execute().data or [])}
            for e in ensayos.data:
                set_ref = e.get("sets_adoracion")
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">🎯 Ensayo · {e.get('sede', '—')}</div>
                    <p>🕒 {e.get('fecha_hora', '—')}</p>
                    <p>📍 {e.get('lugar', '—')}</p>
                    {f"<p>🎤 Set relacionado: {set_ref['servicio']} ({set_ref['fecha']})</p>" if set_ref else ""}
                </div>
                """, unsafe_allow_html=True)
                participantes_nombres = [personas_map.get(pid, "—") for pid in (e.get("participantes") or [])]
                if participantes_nombres:
                    st.caption(f"👥 {', '.join(participantes_nombres)}")
                if e.get("notas"):
                    st.caption(f"📝 {e['notas']}")

                if puede_gestionar:
                    if st.button("🗑️ Eliminar ensayo", key=f"del_ensayo_{e['id']}"):
                        supabase.table("ensayos").delete().eq("id", e["id"]).execute()
                        st.rerun()
                st.markdown("---")
        else:
            st.info("📭 No hay ensayos programados todavía")
    except Exception as e:
        st.error(f"Error al cargar ensayos: {str(e)}")

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

def generar_pdf_tabla(titulo, df):
    pdf = FPDF(orientation="L")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, _pdf_texto_seguro(f"Reporte: {titulo}"), ln=True)
    pdf.set_font("Helvetica", "", 8)

    columnas = list(df.columns)
    ancho_col = 277 / max(len(columnas), 1)

    pdf.set_font("Helvetica", "B", 8)
    for col in columnas:
        pdf.cell(ancho_col, 7, _pdf_texto_seguro(str(col))[:30], border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for _, fila in df.iterrows():
        for col in columnas:
            pdf.cell(ancho_col, 6, _pdf_texto_seguro(str(fila[col]))[:35], border=1)
        pdf.ln()

    return bytes(pdf.output())

def pagina_reportes():
    st.markdown("### 📊 Reportes")

    try:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_canciones = supabase.table("canciones").select("id", count="exact").execute().count
            st.metric("🎵 Canciones", total_canciones)

        with col2:
            total_sets = supabase.table("sets_adoracion").select("id", count="exact").execute().count
            st.metric("📋 Sets", total_sets)

        with col3:
            total_musicos = supabase.table("musicos").select("id", count="exact").execute().count
            st.metric("👥 Músicos", total_musicos)

        with col4:
            total_ensayos = supabase.table("ensayos").select("id", count="exact").execute().count
            st.metric("🎯 Ensayos", total_ensayos)

        # ─── Datos ampliados para los reportes ───
        sets_data = supabase.table("sets_adoracion").select("*").order("fecha", desc=True).execute().data or []
        canciones_data = supabase.table("canciones").select("id,titulo,autor,tonalidad,tempo").order("titulo").execute().data or []
        asign_data = supabase.table("asignaciones").select(
            "*, perfiles(nombre,rol), set_canciones(orden, canciones(titulo), sets_adoracion(fecha,servicio,sede))"
        ).execute().data or []
        uso_canciones_data = supabase.table("set_canciones").select(
            "cancion_id, canciones(titulo, autor), sets_adoracion(fecha, servicio, sede)"
        ).execute().data or []

        st.subheader("🎵 Uso de canciones")
        st.caption("Cuántas veces y cuándo se ha tocado cada canción — útil para reportar a tu licencia musical (CCLI) y para variar el repertorio")
        filas_uso = []
        for u in uso_canciones_data:
            c = u.get("canciones") or {}
            s = u.get("sets_adoracion") or {}
            filas_uso.append({
                "Canción": c.get("titulo", ""),
                "Autor": c.get("autor", ""),
                "Fecha": s.get("fecha", ""),
                "Servicio": s.get("servicio", ""),
                "Sede": s.get("sede", ""),
            })
        df_uso = pd.DataFrame(filas_uso)
        if not df_uso.empty:
            resumen_uso = df_uso.groupby(["Canción", "Autor"]).size().reset_index(name="Veces usada")
            resumen_uso = resumen_uso.sort_values("Veces usada", ascending=False)
            st.dataframe(resumen_uso, use_container_width=True, hide_index=True)
        else:
            st.caption("Aún no hay canciones registradas en ningún set")

        st.subheader("📈 Confirmaciones del equipo")
        if asign_data:
            estados = pd.Series([a.get("estado_confirmacion", "Pendiente") for a in asign_data]).value_counts()
            cconf1, cconf2, cconf3 = st.columns(3)
            cconf1.metric("🟢 Confirmados", int(estados.get("Confirmado", 0)))
            cconf2.metric("🟡 Pendientes", int(estados.get("Pendiente", 0)))
            cconf3.metric("🔴 Rechazados", int(estados.get("Rechazado", 0)))
        else:
            st.caption("Aún no hay asignaciones registradas")

        st.subheader("📥 Exportar datos")

        # Tabla completa de asignaciones (para CSV/Excel/PDF)
        filas_asignaciones = []
        for a in asign_data:
            sc = a.get("set_canciones") or {}
            s = sc.get("sets_adoracion") or {}
            filas_asignaciones.append({
                "Fecha": s.get("fecha", ""),
                "Servicio": s.get("servicio", ""),
                "Sede": s.get("sede", ""),
                "Canción": (sc.get("canciones") or {}).get("titulo", ""),
                "Persona": (a.get("perfiles") or {}).get("nombre", ""),
                "Rol": a.get("tipo_rol", ""),
                "Estado": a.get("estado_confirmacion", "Pendiente"),
            })
        df_asignaciones = pd.DataFrame(filas_asignaciones)
        df_sets = pd.DataFrame(sets_data)
        df_canciones = pd.DataFrame(canciones_data)
        df_uso_export = resumen_uso if not df_uso.empty else pd.DataFrame()

        formato = st.radio("Formato de descarga", ["CSV", "Excel", "PDF"], horizontal=True)
        reporte = st.selectbox("Qué reporte quieres descargar", [
            "Sets", "Canciones", "Asignaciones y confirmaciones", "Uso de canciones"
        ])

        df_elegido = {
            "Sets": df_sets, "Canciones": df_canciones,
            "Asignaciones y confirmaciones": df_asignaciones,
            "Uso de canciones": df_uso_export
        }[reporte]

        if df_elegido.empty:
            st.info("No hay datos disponibles para este reporte todavía")
        elif formato == "CSV":
            csv = df_elegido.to_csv(index=False).encode("utf-8")
            st.download_button("📄 Descargar CSV", csv, f"{reporte.lower().replace(' ', '_')}.csv", "text/csv")
        elif formato == "Excel":
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_elegido.to_excel(writer, index=False, sheet_name=reporte[:31])
            st.download_button(
                "📊 Descargar Excel", buffer.getvalue(),
                f"{reporte.lower().replace(' ', '_')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif formato == "PDF":
            pdf_bytes = generar_pdf_tabla(reporte, df_elegido)
            st.download_button("📕 Descargar PDF", pdf_bytes, f"{reporte.lower().replace(' ', '_')}.pdf", "application/pdf")

    except Exception as e:
        st.error(f"Error al cargar reportes: {str(e)}")

# ─────────── NAVEGACIÓN PRINCIPAL ───────────


def main():
    if not st.session_state.usuario:
        if st.session_state.get("pagina_registro"):
            registro()
        else:
            login()
        return
    
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
        
        # ─── MENÚ DINÁMICO (ACTUALIZADO CON COORDINADOR DE ADORACIÓN) ───
        menu_items = {
            "🎼 Canciones": pagina_canciones,
            "📋 Sets": pagina_sets,
            "✅ Mis Servicios": pagina_mis_asignaciones,
        }
        
        # Coordinador de Adoración, Multimedia y Director de Alabanza ven Músicos y Técnicos
        if st.session_state.rol in ["Coordinador de Adoración", "Coordinador de Multimedia", "Director de Alabanza"]:
            menu_items["👥 Músicos"] = pagina_musicos
            menu_items["🔧 Técnicos"] = pagina_tecnicos
        
        # Coordinador de Adoración y Multimedia ven Recursos
        if st.session_state.rol in ["Coordinador de Adoración", "Coordinador de Multimedia"]:
            menu_items["🖼 Recursos"] = pagina_recursos
        
        # Todos ven Calendario y Chat
        menu_items["📅 Calendario"] = pagina_calendario
        menu_items["🎯 Ensayos"] = pagina_ensayos
        menu_items["💬 Chat"] = pagina_chat
        
        # Reportes para coordinadores y directores
        if st.session_state.rol in ["Coordinador de Adoración", "Coordinador de Multimedia", "Director de Alabanza"]:
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
    
    menu_items[opcion]()

if __name__ == "__main__":
    main()
