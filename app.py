import streamlit as st
from google import genai
from google.genai import types
import requests
import datetime
import random
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="English Speaking & Writing - Level 6",
    page_icon="🎓",
    layout="centered"
)

# Inicializar cliente de Gemini con la API Key de los Secrets
@st.cache_resource
def init_gemini():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

try:
    gemini_client = init_gemini()
except Exception as e:
    st.error(f"Error al iniciar Gemini: {e}")
    st.stop()

# URL del Webhook de Google Apps Script (opcional)
WEBHOOK_URL = st.secrets.get("SHEET_WEBHOOK_URL", "")

# --- FUNCIONES AUXILIARES ---
def get_questions_from_sheet():
    return [
        "What did you do last weekend that was really fun?",
        "If you could travel anywhere next summer, where would you go and why?",
        "Have you ever had a challenging day at work or school? What happened?",
        "What are your plans for the upcoming holiday?",
        "Tell me about your favorite daily routine and why you like it."
    ]

# --- INTERFAZ DE USUARIO ---
st.title("🎓 Pre-Intermediate 2 Speaking & Writing Practice")
st.markdown("Responde la siguiente pregunta por escrito y graba tu voz para recibir retroalimentación instantánea de tu profesor virtual.")

# Inicializar pregunta aleatoria en la sesión del alumno
if "current_question" not in st.session_state:
    questions_pool = get_questions_from_sheet()
    st.session_state.current_question = random.choice(questions_pool)

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

                # Llamada usando el modelo estable gemini-1.5-flash
                response = None
                max_retries = 3
                retry_delay = 2
                
                for attempt in range(max_retries):
                    try:
                        response = gemini_client.models.generate_content(
                            model='gemini-1.5-flash',
                            contents=contents,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.3
                            )
                        )
                        break 
                    except Exception as api_err:
                        if "503" in str(api_err) and attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2 
                            continue
                        else:
                            raise api_err 
                
                evaluation_result = response.text

                # Enviar a Google Sheets mediante Webhook (si está configurado)
                if WEBHOOK_URL:
                    payload = {
                        "date": str(datetime.datetime.now()),
                        "studentName": student_name,
                        "question": st.session_state.current_question,
                        "writtenResponse": written_response,
                        "evaluation": evaluation_result
                    }
                    requests.post(WEBHOOK_URL, json=payload)

                st.success("¡Evaluación completada con éxito!")
                st.markdown("### 📋 Retroalimentación de tu Profesor:")
                st.markdown(evaluation_result)

            except Exception as e:
                st.error(f"Ocurrió un error al procesar tu envío: {e}")
