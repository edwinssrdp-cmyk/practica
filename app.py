import streamlit as st
import gspread
from google.oauth2 import service_account
from google import genai
from google.genai import types
import datetime
import random

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="English Speaking & Writing - Level 6",
    page_icon="🎓",
    layout="centered"
)

# --- CONFIGURAR CREDENCIALES ---
@st.cache_resource
def init_connections():
    # Scopes necesarios para Google Sheets y Drive
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Cargar los secretos de Google desde Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Autenticación moderna con google-auth (evita errores de padding base64)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=scopes
    )
    client = gspread.authorize(creds)
    
    # Abrir la hoja de cálculo
    sheet_name = st.secrets["SHEET_NAME"]
    spreadsheet = client.open(sheet_name)
    
    # Inicializar cliente de Gemini con la API Key
    gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    return spreadsheet, gemini_client

try:
    spreadsheet, gemini_client = init_connections()
except Exception as e:
    st.error(f"Error de configuración inicial: {e}")
    st.stop()

# --- FUNCIONES AUXILIARES ---
def get_random_question():
    try:
        worksheet = spreadsheet.worksheet("Preguntas")
        questions = worksheet.col_values(1)[1:] # Ignorar cabecera
        if not questions:
            return "Tell me about your favorite daily routine."
        return random.choice(questions)
    except Exception:
        return "What did you do last weekend?"

# --- INTERFAZ DE USUARIO ---
st.title("🎓 Pre-Intermediate 2 Speaking & Writing Practice")
st.markdown("Responde la siguiente pregunta por escrito y graba tu voz para recibir retroalimentación instantánea de tu profesor virtual.")

# Inicializar pregunta aleatoria en la sesión del alumno
if "current_question" not in st.session_state:
    st.session_state.current_question = get_random_question()

# Caja de pregunta
st.info(f"**Pregunta asignada:**\n\n{st.session_state.current_question}")

with st.form("evaluation_form"):
    student_name = st.text_input("Full Name / Nombre Completo:")
    
    written_response = st.text_area(
        "Your Written Answer / Tu respuesta escrita:",
        placeholder="Type your response here in English..."
    )
    
    st.markdown("---")
    st.markdown("### 🎙️ Voice Recording / Grabación de Voz")
    st.markdown("Haz clic en el botón de grabación para registrar tu respuesta oral:")
    
    # Componente nativo de Streamlit para grabar audio directo desde el navegador (PC o Móvil)
    audio_file = st.audio_input("Graba tu voz respondiendo la pregunta")
    
    submitted = st.form_submit_button("🚀 Submit for Feedback / Enviar para Evaluación")

if submitted:
    if not student_name.strip() or not written_response.strip():
        st.warning("⚠️ Por favor ingresa tu nombre y escribe tu respuesta antes de enviar.")
    else:
        with st.spinner("🤖 Analizando tu respuesta escrita y tu voz con IA... Por favor espera unos segundos."):
            try:
                audio_bytes = None
                mime_type = "audio/wav"
                
                if audio_file is not None:
                    audio_bytes = audio_file.read()
                    mime_type = audio_file.type 

                # Instrucción del sistema para Gemini
                system_instruction = (
                    "You are a supportive, encouraging English Language Teacher evaluating a Pre-Intermediate 2 (CEFR A2+/B1 level) student. "
                    "Structure your feedback in friendly Spanish, using English for examples/corrections:\n\n"
                    "1. 📝 **Gramática y Estructura:** Breve análisis de la respuesta escrita. Señala errores o confirma si está bien.\n"
                    "2. 💡 **Sugerencia de Naturalidad:** Cómo expresar la misma idea de forma más fluida u holgada.\n"
                    "3. 🎙️ **Pronunciación y Fluidez (si hay audio):** Evalúa la claridad del audio, entonación y palabras clave a mejorar. Si no hay audio, indícalo.\n"
                    "4. ⭐ **Puntaje Estimado:** Asigna una puntuación general de 1 a 10."
                )

                contents = [
                    f"Pregunta asignada: \"{st.session_state.current_question}\"\nRespuesta escrita del estudiante: \"{written_response}\"\n\nPor favor evalúa el texto y el audio adjunto."
                ]

                if audio_bytes:
                    contents.append(
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type=mime_type,
                        )
                    )

                response = gemini_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3
                    )
                )
                
                evaluation_result = response.text

                # Guardar en Google Sheets (Pestaña Respuestas)
                respuestas_sheet = spreadsheet.worksheet("Respuestas")
                audio_status = "Audio registrado y evaluado" if audio_bytes else "Sin audio"
                
                respuestas_sheet.append_row([
                    str(datetime.datetime.now()),
                    student_name,
                    st.session_state.current_question,
                    written_response,
                    audio_status,
                    evaluation_result
                ])

                st.success("¡Evaluación completada con éxito!")
                st.markdown("### 📋 Retroalimentación de tu Profesor:")
                st.markdown(evaluation_result)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar tu envío: {e}")
