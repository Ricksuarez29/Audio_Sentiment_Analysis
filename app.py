# app.py - Main Streamlit application for Banco Sabadell Sentiment Analysis

import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from io import StringIO
import streamlit.components.v1 as components
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd
import numpy as np


# Import our custom modules
from config import APP_CONFIG, COHERE_API_KEY, ASSEMBLYAI_API_KEY, DEFAULT_PROMPTS, UPLOAD_CONFIG, ASSEMBLYAI_SETTINGS
from analyzer import SabadellSentimentAnalyzer
from utils import ConversationParser, ExportManager, FormatExamples
from audio_transcriber import AudioTranscriber

# Page configuration
st.set_page_config(**APP_CONFIG)

def main():
    """Main application function"""
    
    # App header
    st.title("🏦 Banco Sabadell - Análisis de Sentimientos")
    st.markdown("### 📞 Herramienta de Análisis de Mejora Conversacional")
    st.markdown("---")
    
    # Initialize session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = None
    if 'transcriber' not in st.session_state:
        st.session_state.transcriber = None
    if 'api_keys_configured' not in st.session_state:
        st.session_state.api_keys_configured = {"cohere": False, "assemblyai": False}
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # API Keys Configuration
        st.subheader("🔑 API Keys")
        
        # Cohere API Key
        cohere_source = st.radio(
            "Cohere API Key:",
            ["Usar config.py", "Ingresar manualmente"],
            key="cohere_source"
        )
        
        cohere_key = None
        if cohere_source == "Usar config.py":
            if COHERE_API_KEY and COHERE_API_KEY != "your-cohere-api-key-here":
                cohere_key = COHERE_API_KEY
                st.success("✅ Cohere API Key cargada")
            else:
                st.error("❌ Configura COHERE_API_KEY en config.py")
        else:
            cohere_key = st.text_input("Cohere API Key", type="password", key="cohere_manual")
            if cohere_key:
                st.success("✅ Cohere API Key ingresada")
        
        # AssemblyAI API Key
        assemblyai_source = st.radio(
            "AssemblyAI API Key:",
            ["Usar config.py", "Ingresar manualmente"],
            key="assemblyai_source"
        )
        
        assemblyai_key = None
        if assemblyai_source == "Usar config.py":
            if ASSEMBLYAI_API_KEY and ASSEMBLYAI_API_KEY != "your-assemblyai-api-key-here":
                assemblyai_key = ASSEMBLYAI_API_KEY
                st.success("✅ AssemblyAI API Key cargada")
            else:
                st.info("💡 Configura ASSEMBLYAI_API_KEY en config.py")
        else:
            assemblyai_key = st.text_input("AssemblyAI API Key", type="password", key="assemblyai_manual")
            if assemblyai_key:
                st.success("✅ AssemblyAI API Key ingresada")
        
        # Initialize services
        if cohere_key and not st.session_state.api_keys_configured["cohere"]:
            st.session_state.analyzer = SabadellSentimentAnalyzer(cohere_key)
            st.session_state.api_keys_configured["cohere"] = True
        
        if assemblyai_key and not st.session_state.api_keys_configured["assemblyai"]:
            st.session_state.transcriber = AudioTranscriber(assemblyai_key)
            st.session_state.api_keys_configured["assemblyai"] = True
        
        # Test connections
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.analyzer and st.button("🔗 Test Cohere", key="test_cohere"):
                with st.spinner("Testing..."):
                    if st.session_state.analyzer.test_connection():
                        st.success("✅ Cohere OK!")
                    else:
                        st.error("❌ Cohere failed")
        
        with col2:
            if st.session_state.transcriber and st.button("🔗 Test AssemblyAI", key="test_assemblyai"):
                with st.spinner("Testing..."):
                    if st.session_state.transcriber.test_connection():
                        st.success("✅ AssemblyAI OK!")
                    else:
                        st.error("❌ AssemblyAI failed")
        
        st.divider()
        
        # Format selection
        st.subheader("📄 Formato de Entrada")
        format_type = st.selectbox(
            "Selecciona el formato:",
            ["Simple Format", "Timestamped Format", "JSON Format"]
        )
        
        # Show format examples
        with st.expander("📋 Ver ejemplo"):
            example_text = FormatExamples.get_example(format_type)
            st.code(example_text, language="text" if format_type != "JSON Format" else "json")
        
        st.divider()
        
        # Custom prompt
        st.subheader("🎯 Prompt Personalizado")
        use_custom_prompt = st.checkbox("Usar prompt personalizado")
        
        custom_prompt = None
        if use_custom_prompt:
            custom_prompt = st.text_area(
                "Prompt:",
                value=DEFAULT_PROMPTS["spanish_banking"].strip(),
                height=150
            )
    
    # Main content area with tabs
    main_tab1, main_tab2 , vader_tab = st.tabs(["🎤 Transcripción de Audio","📝 Análisis de Texto","🧪 Análisis VADER"])
    
    with main_tab1:
        # Audio transcription interface
        show_audio_transcription_tab()
    
    with main_tab2:
        # Existing text analysis interface
        show_text_analysis_tab(format_type, custom_prompt)

    with vader_tab:
        show_vader_analysis_tab(format_type, custom_prompt)




# ------ # Audio transcription tab content

def show_audio_transcription_tab():
    """Show the audio transcription tab content"""
    
    st.subheader("🎤 Transcripción de Audio a Conversación")
    
    if not st.session_state.transcriber:
        st.warning("⚠️ Configura tu API Key de AssemblyAI en la barra lateral para usar esta función")
        st.info("💡 Obtén tu API key gratuita en [assemblyai.com](https://assemblyai.com)")
        return
    
    # Language selection
    audio_language = st.selectbox(
        "Idioma del audio:",
        ["es", "en"],
        format_func=lambda x: "Español" if x == "es" else "English",
        key="audio_language"
    )
    
    # Audio settings
    with st.expander("⚙️ Configuración Avanzada"):
        speakers_expected = st.number_input(
            "Número de hablantes esperados:",
            min_value=2,
            max_value=5,
            value=2,
            help="2 = Cliente + Agente (recomendado para llamadas bancarias)"
        )
        
        dual_channel = st.checkbox(
            "Audio estéreo con canales separados",
            value=False,
            help="Marcar si el audio tiene cada hablante en un canal diferente"
        )
    
    # Audio file upload
    uploaded_audio = st.file_uploader(
        "Sube archivo de audio",
        type=UPLOAD_CONFIG['allowed_audio_extensions'],
        help=f"Formatos soportados: {', '.join(UPLOAD_CONFIG['allowed_audio_extensions'])}",
        key="audio_file_upload"
    )
    
    if uploaded_audio is not None:
        # Show audio player
        st.audio(uploaded_audio)
    
        
        # Mostrar información del archivo en tres columnas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Archivo", uploaded_audio.name)
        with col2:
            file_size = len(uploaded_audio.getbuffer()) / (1024 * 1024)
            st.metric("Tamaño", f"{file_size:.1f} MB")

        # Check file size
        with col3:
            if file_size > UPLOAD_CONFIG['max_file_size_mb']:
                st.error(f"❌ Muy grande (máx: {UPLOAD_CONFIG['max_file_size_mb']}MB)")
            else:
                st.success("✅ Tamaño OK")
        
        # Transcription button
        if file_size <= UPLOAD_CONFIG['max_file_size_mb']:
            if st.button("🎤 Transcribir Audio", type="primary", key="transcribe_audio"):
                with st.spinner("🔄 Transcribiendo audio..."):
                    result = st.session_state.transcriber.transcribe_audio(
                        uploaded_audio, 
                        audio_language
                    )
                          
                if result.get("success"):
                    st.success("✅ Transcripción completada!")

                    st.subheader("📝 Conversación Transcrita")

                    # Main result
                    transcribed_text = result["formatted_conversation"]

                    #Save to session state
                    st.session_state.transcribed_text = transcribed_text

                    st.text_area(
                        "Resultado (copia esto al analizador de texto):",
                        transcribed_text,
                        height=300,
                        help="Copia este texto y úsalo en la pestaña 'Análisis de Texto'"
                    )

                    # Show metadata
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Confianza", f"{result['confidence']:.1%}")
                    with col2:
                        st.metric("Duración", f"{result['audio_duration']:.1f}s")
                    with col3:
                        st.metric("Hablantes", result['total_speakers'])
                    with col4:
                        st.metric("Segmentos", len(result['segments']))
                    
                    # Show detailed segments
                    with st.expander("🔍 Ver segmentos detallados"):
                        segments_df = pd.DataFrame(result['segments'])
                        st.dataframe(
                            segments_df[['timestamp', 'speaker', 'text', 'confidence']],
                            use_container_width=True
                        )
                    
                    # Show full transcript
                    with st.expander("📄 Ver transcripción completa"):
                        st.write(result.get("full_transcript", ""))
                    



# ------ # Text analysis with VADER -----------

nltk.download('vader_lexicon')

def show_vader_analysis_tab(format_type, custom_prompt):
    """Show the VADER analysis tab content for the customer's speech"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Entrada de Conversación")
        
        # Opciones de entrada. Se agrega la opción "🎙️ Usar transcripción" si existe en session_state.
        methods = ["✏️ Texto directo", "📁 Subir archivo"]
        if "transcribed_text" in st.session_state:
            methods.insert(0, "🎙️ Usar transcripción")
            
        input_method = st.radio(
            "Método de entrada:",
            methods,
            horizontal=True,
            key="vader_text_input_method"
        )
        
        conversation_text = ""
        
        if input_method == "🎙️ Usar transcripción":
            conversation_text = st.session_state["transcribed_text"]
            st.text_area(
                f"Conversación transcrita en formato {format_type}:",
                conversation_text,
                height=300,
                key="vader_text_transcribed",
                disabled=True
            )
        elif input_method == "✏️ Texto directo":
            conversation_text = st.text_area(
                f"Conversación en formato {format_type}:",
                height=300,
                placeholder="Pega aquí la conversación...",
                key="vader_text_conversation"
            )
        else:
            uploaded_file = st.file_uploader(
                "Sube archivo de conversación",
                type=UPLOAD_CONFIG['allowed_text_extensions'],
                key="vader_text_file_upload"
            )
            
            if uploaded_file is not None:
                try:
                    conversation_text = str(uploaded_file.read(), UPLOAD_CONFIG['encoding'])
                    st.success(f"✅ Archivo cargado: {uploaded_file.name}")
                    with st.expander("Vista previa"):
                        st.text_area("Contenido:", conversation_text, height=150, disabled=True)
                except Exception as e:
                    st.error(f"❌ Error leyendo archivo: {str(e)}")
                    
    with col2:
        st.subheader("👁️ Vista Previa")
        
        if not conversation_text.strip():
            st.info("💡 Ingresa una conversación para ver la vista previa")
            segments = None
        else:
            # Parsear la conversación usando el formato seleccionado
            segments = ConversationParser.parse_conversation_text(conversation_text, format_type)
            
            if not segments:
                st.warning("⚠️ No se detectaron segmentos válidos")
            else:
                validation = ConversationParser.validate_segments(segments)
                
                if not validation['valid']:
                    st.error(f"❌ {validation['error']}")
                    segments = None
                else:
                    stats = validation['stats']
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Segmentos", stats['total_segments'])
                    with col_b:
                        st.metric("Hablantes", len(stats['speakers']))

                        
                    st.write("**Hablantes:**", ", ".join(stats['speakers']))
                    
                    # Vista previa de algunos segmentos
                    with st.expander(f"Ver segmentos ({len(segments)})"):
                        for i, seg in enumerate(segments[:5]):
                            timestamp = seg.get('timestamp', 'N/A')
                            text = seg['text'][:80] + "..." if len(seg['text']) > 80 else seg['text']
                            st.write(f"**{i+1}.** `[{timestamp}]` **{seg['speaker']}:** {text}")
                        if len(segments) > 5:
                            st.write(f"... y {len(segments)-5} más")
                            
    st.divider()
    st.subheader("🚀 Análisis de Sentimientos con VADER")
    
    if segments is None:
        st.error("❌ No hay segmentos válidos para analizar")
    else:
        if st.button("🔍 Analizar con VADER", type="primary", key="analyze_vader"):
            with st.spinner("🔄 Analizando conversación..."):
                customer_segments = [
                    seg for seg in segments 
                    if any(alias in seg['speaker'].lower() for alias in ['cliente', 'customer', 'client'])
                ]

                if not customer_segments:
                    st.error("❌ No se detectaron segmentos del cliente para analizar")
                    return
                
                # Call the new function to analyze if the call solved the problem
                solved_indicator = st.session_state.analyzer.analyze_call_solution(conversation_text)
                
                # Save the value in the session for later use in other sections
                st.session_state["solved_indicator"] = solved_indicator             

                sid = SentimentIntensityAnalyzer()
                results_list = []

                for idx, seg in enumerate(customer_segments):
                    sentence = seg['text']
                    scores = sid.polarity_scores(sentence)
                    results_list.append({
                        "Index": idx + 1,
                        "Timestamp": seg.get('timestamp', 'N/A'),
                        "Speaker": seg['speaker'],
                        "Sentence": sentence,
                        "Negative": scores["neg"],
                        "Neutral": scores["neu"],
                        "Positive": scores["pos"],
                        "Compound": scores["compound"]
                    })

                df_results = pd.DataFrame(results_list)

                st.success("✅ ¡Análisis completado!")

                # Sección de métricas clave
                st.subheader("📊 Resultados del Análisis")

                if not df_results.empty:
                    # Calculate the average sentiment scores
                    total_segments = df_results.shape[0]
                    if total_segments < 6:
                        # Not enough segments for partitioning; use overall average.
                        overall_avg = df_results["Compound"].mean()
                        first_avg = overall_avg
                        middle_avg = overall_avg
                        last_avg = overall_avg

                    elif total_segments < 10:
                        # Short call: Use first 2, middle 2, and final 2.
                        first_avg = df_results.iloc[:2]["Compound"].mean()
                        last_avg = df_results.iloc[-2:]["Compound"].mean()
                        mid_index = total_segments // 2
                        # For even number of segments, take the two central segments.
                        if total_segments % 2 == 0:
                            middle_avg = df_results.iloc[mid_index - 1: mid_index + 1]["Compound"].mean()
                        else:
                            # For odd, select the middle two segments (if possible).
                            if mid_index - 1 >= 0:
                                middle_avg = df_results.iloc[mid_index - 1: mid_index + 1]["Compound"].mean()
                            else:
                                middle_avg = df_results.iloc[mid_index]["Compound"]

                    elif total_segments < 30:
                        # Medium call: first 3 segments, middle one, and final 3.
                        first_avg = df_results.iloc[:3]["Compound"].mean()
                        last_avg = df_results.iloc[-3:]["Compound"].mean()
                        mid_index = total_segments // 2
                        # Use a window of 5 segments.
                        start_mid = max(0, mid_index - 2)
                        end_mid = start_mid + 5
                        middle_avg = df_results.iloc[start_mid:end_mid]["Compound"].mean()

                    else:
                        # Big call: first 5 segments, a window of 5 centered around the middle, and final 5 segments.
                        first_avg = df_results.iloc[:5]["Compound"].mean()
                        last_avg = df_results.iloc[-5:]["Compound"].mean()
                        mid_index = total_segments // 2
                        # Use a window of 5 segments.
                        start_mid = max(0, mid_index - 2)
                        end_mid = start_mid + 5
                        middle_avg = df_results.iloc[start_mid:end_mid]["Compound"].mean()


                    # Raw improvement (difference between final and initial average)
                    raw_improvement = last_avg - first_avg

                    # Get the solution indicator previously stored (1 = solved, 0 = not)
                    solved_indicator = st.session_state.get("solved_indicator", 0)
                    call_solved_status = "Resuelto" if solved_indicator == 1 else "No Resuelto"


                    # This index evaluates the recovery potential relative to the negative starting point.
                    # If the call began with a negative sentiment, the maximum possible improvement is (1 - first_avg).
                    if solved_indicator == 1:
                        # Recovery score is positive if problem was solved, even if sentiment drops
                        if last_avg < first_avg:
                            # Drop in sentiment, but solved → interpret as emotionally costly resolution
                            sentiment_recovery_index = 0.5 * (1 + (last_avg - first_avg))  # scaled drop
                        else:
                            # Regular improvement case
                            sentiment_recovery_index = 1.0 * (last_avg - first_avg + 1) / 2  # normalized to 0–1
                    else:
                        # Not solved → use negative or zero score
                        sentiment_recovery_index = min(0, last_avg - first_avg)

                    # Convert the recovery index to percentage scale
                    sri_percent = sentiment_recovery_index * 100

                    # Also calculate the overall emotional health average (Compound mean percentage)
                    avg_compound = df_results["Compound"].mean()

                    # Now, display the enhanced metrics in a row of columns
                    col1, col2, col3, col5, = st.columns(4)
                    with col1:
                        st.metric("Estado de Resolución", call_solved_status)
                    with col2:
                        delta_str = "Mejoró" if raw_improvement >= 0 else "Empeoró"
                        st.metric(
                            label="Estado del Cliente",
                            value=f"{raw_improvement:+.2f}",
                            delta=delta_str,
                            delta_color="normal" if raw_improvement >= 0 else "inverse"
                        )
                    with col3:
                        st.metric("Índice de Recuperación", f"{sri_percent:.1f}%")

                    with col5:
                        st.metric("Salud Emocional Promedio", f"{avg_compound:.1f}")

                    # Helper function for colored sentiment text.
                    def colored_sentiment(sentiment):
                        if sentiment == "positive":
                            return '<span style="color:green; font-weight:bold;">positive</span>'
                        elif sentiment == "negative":
                            return '<span style="color:red; font-weight:bold;">negative</span>'
                        else:
                            return '<span style="color:orange; font-weight:bold;">neutral</span>'

                    # Helper function for colored trend text.
                    def colored_trend(trend_value):
                        if trend_value == "improved":
                            return '<span style="color:green; font-weight:bold;">improved</span>'
                        elif trend_value == "worsened":
                            return '<span style="color:red; font-weight:bold;">worsened</span>'
                        else:
                            return '<span style="color:orange; font-weight:bold;">remained stable</span>'

                    # Determine sentiment category from a compound score.
                    def sentiment_category(score):
                        if score >= 0.05:
                            return "positive"
                        elif score <= -0.05:
                            return "negative"
                        else:
                            return "neutral"

                    # Assume that first_avg, middle_avg, and last_avg were determined 
                    # from partitioning the conversation according to its length.
                    initial_sentiment = sentiment_category(first_avg)
                    middle_sentiment = sentiment_category(middle_avg)
                    final_sentiment = sentiment_category(last_avg)

                    # Determine the trend from the beginning to the mid part.
                    tolerance = 0.01
                    if abs(middle_avg - first_avg) < tolerance:
                        trend = "remained stable"
                    elif middle_avg > first_avg:
                        trend = "improved"
                    else:
                        trend = "worsened"

                    # Build the final summary message.
                    if solved_indicator == 1:
                        # Call was solved → show positive phrases in green.
                        if final_sentiment == "positive":
                            final_message = (
                                f"The call began with a {colored_sentiment(initial_sentiment)} sentiment, "
                                f"{colored_trend(trend)} during the mid part of the call, and finally ended with a "
                                f"{colored_sentiment(final_sentiment)} tone as the agent was "
                                f"<span style='color:green; font-weight:bold;'>able to solve</span> the problem."
                            )
                        elif final_sentiment == "neutral":
                            final_message = (
                                f"The call began with a {colored_sentiment(initial_sentiment)} sentiment, "
                                f"{colored_trend(trend)} during the mid part of the call, and although it ended with a "
                                f"{colored_sentiment(final_sentiment)} tone, the agent "
                                f"<span style='color:green; font-weight:bold;'>managed to solve</span> the problem."
                            )
                        elif final_sentiment == "negative":
                            final_message = (
                                f"The call began with a {colored_sentiment(initial_sentiment)} sentiment, "
                                f"{colored_trend(trend)} during the mid part of the call, and although it ended with a "
                                f"{colored_sentiment(final_sentiment)} tone, the problem was "
                                f"<span style='color:green; font-weight:bold;'>successfully resolved</span>."
                            )
                    else:
                        # Call not solved → show outcome text in a dark red
                        final_message = (
                            f"The call began with a {colored_sentiment(initial_sentiment)} sentiment, "
                            f"{colored_trend(trend)} during the mid part of the call, and finally ended with a "
                            f"{colored_sentiment(final_sentiment)} tone as the agent was "
                            f"<span style='color:firebrick; font-weight:bold;'>not able to solve</span> the problem."
                        )

                    final_message_html = f"""
                    <div style="text-align: center; font-size: 24px; margin: 20px 0;">
                        {final_message}
                    </div>
                    """
                    st.markdown(final_message_html, unsafe_allow_html=True)
  

  
            
##-----------------------------------------------------------------------------------                   

                st.divider()
                st.subheader("📈 Evolución del Sentimiento (Compound Score)")

                fig_line = px.line(
                    df_results,
                    x="Index",
                    y="Compound",
                    hover_data=["Timestamp", "Sentence"],
                    markers=True,
                    title="Sentimiento Compound a lo largo de la conversación",
                )
                fig_line.update_layout(
                    xaxis_title="Secuencia del Cliente",
                    yaxis_title="Sentimiento (Compound)",
                    yaxis_range=[-1, 1],
                    height=400
                )
                fig_line.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_line, use_container_width=True)


                z = np.array([df_results["Compound"].tolist()])
                x = df_results["Index"].tolist()

                fig = go.Figure()

                heatmap = go.Heatmap(
                    z=z,
                    x=x,
                    y=["Cliente"],  # Una sola fila para el cliente
                    colorscale="RdYlGn",
                    zmin=-1,
                    zmax=1,
                    showscale=True,
                    colorbar=dict(title="Compound")
                )
                fig.add_trace(heatmap)

                # Para agregar anotaciones a cada celda
                annotations = []
                for i, val in enumerate(z[0]):
                    # Escogemos el color del texto en función del contraste (opcional)
                    text_color = "black" if val > -0.2 and val < 0.2 else "white"
                    annotations.append(
                        dict(
                            x=x[i],
                            y="Cliente",
                            text=str(round(val, 2)),
                            font=dict(color=text_color, size=12),
                            showarrow=False,
                            xanchor="center",
                            yanchor="middle"
                        )
                    )

                fig.update_layout(
                    annotations=annotations,
                    title="🌡️ Mapa de Calor - Sentimiento Compound por Turno del Cliente",
                    xaxis=dict(title="Secuencia del Cliente"),
                    yaxis=dict(showticklabels=False),
                    height=230,
                    margin=dict(l=20, r=20, t=40, b=20)
                )

                st.plotly_chart(fig, use_container_width=True)





# ------ # Text analysis tab content
def show_text_analysis_tab(format_type, custom_prompt):
    """Show the text analysis tab content"""
    
    col1, col2 = st.columns([2, 1])
        
    with col1:
        st.subheader("📝 Entrada de Conversación")
        
        # Input method
        methods = ["✏️ Texto directo", "📁 Subir archivo"]
        if "transcribed_text" in st.session_state:
            methods.insert(0, "🎙️ Usar transcripción")

        input_method = st.radio(
            "Método de entrada:",
            methods,
            horizontal=True,
            key="text_input_method"
        )
        
        conversation_text = ""
        
        if input_method == "🎙️ Usar transcripción":
            conversation_text = st.session_state["transcribed_text"]
            st.text_area(
                f"Conversación transcrita en formato {format_type}:",
                conversation_text,
                height=300,
                key="text_transcribed",
                disabled=True
            )

        elif input_method == "✏️ Texto directo":
            conversation_text = st.text_area(
                f"Conversación en formato {format_type}:",
                height=300,
                placeholder="Pega aquí tu conversación...",
                key="text_conversation"
            )

        else:
            uploaded_file = st.file_uploader(
                "Sube archivo de conversación",
                type=UPLOAD_CONFIG['allowed_text_extensions'],
                key="text_file_upload"
            )

            if uploaded_file is not None:
                try:
                    conversation_text = str(uploaded_file.read(), UPLOAD_CONFIG['encoding'])
                    st.success(f"✅ Archivo cargado: {uploaded_file.name}")
                    with st.expander("Vista previa"):
                        st.text_area("Contenido:", conversation_text, height=150, disabled=True)
                except Exception as e:
                    st.error(f"❌ Error leyendo archivo: {str(e)}")

    
    with col2:
        st.subheader("👁️ Vista Previa")
        
        if not conversation_text.strip():
            st.info("💡 Ingresa una conversación para ver la vista previa")
            segments = None
        else:
            # Parse conversation
            segments = ConversationParser.parse_conversation_text(conversation_text, format_type)
            
            if not segments:
                st.warning("⚠️ No se detectaron segmentos válidos")
            else:
                # Validate segments
                validation = ConversationParser.validate_segments(segments)
                
                if not validation['valid']:
                    st.error(f"❌ {validation['error']}")
                    segments = None
                else:
                    stats = validation['stats']
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Segmentos", stats['total_segments'])
                    with col_b:
                        st.metric("Hablantes", len(stats['speakers']))
                    
                    st.write("**Hablantes:**", ", ".join(stats['speakers']))
                    
                    # Preview segments
                    with st.expander(f"Ver segmentos ({len(segments)})"):
                        for i, seg in enumerate(segments[:5]):
                            timestamp = seg.get('timestamp', 'N/A')
                            text = seg['text'][:80] + "..." if len(seg['text']) > 80 else seg['text']
                            st.write(f"**{i+1}.** `[{timestamp}]` **{seg['speaker']}:** {text}")
                        
                        if len(segments) > 5:
                            st.write(f"... y {len(segments) - 5} más")
    
    # Analysis section
    st.divider()
    st.subheader("🚀 Análisis de Sentimientos")
    
    if not st.session_state.analyzer:
        st.error("❌ Configura tu API Key de Cohere primero")
    elif not segments:
        st.error("❌ No hay segmentos válidos para analizar")
    else:
        if st.button("🔍 Analizar Conversación", type="primary", key="analyze_text"):
            with st.spinner("🔄 Analizando conversación..."):
                try:
                    # Perform analysis
                    results = st.session_state.analyzer.analyze_full_call(segments, custom_prompt)
                    
                    st.success("✅ ¡Análisis completado!")
                    
                    # Display results
                    show_results(results)
                    
                except Exception as e:
                    st.error(f"❌ Error durante el análisis: {str(e)}")




def show_results(results):
    """Display analysis results"""
    # Key metrics
    st.subheader("📊 Resultados del Análisis")
    metrics = results['metrics']
    summary = results['summary']
    customer_segments = [s for s in results['analyzed_segments'] if s['speaker'].lower() in ['customer', 'cliente', 'client']]
    # Calculate sentiment volatility (std dev of sentiment score * intensity)
    sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1}
    sentiment_scores = [sentiment_map[s['sentiment']] * s['intensity'] for s in customer_segments]
    volatility = float(np.std(sentiment_scores)) if sentiment_scores else 0.0
    # Calculate time spent in each sentiment (proportion)
    total = len(customer_segments)
    time_in_sentiment = {k: 0 for k in ['positive', 'neutral', 'negative']}
    for s in customer_segments:
        time_in_sentiment[s['sentiment']] += 1
    for k in time_in_sentiment:
        time_in_sentiment[k] = (time_in_sentiment[k] / total * 100) if total else 0
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Mejora del Cliente",
            f"{metrics['customer_improvement']:+.1f}",
            delta=f"{'Mejoró' if metrics['customer_improvement'] > 0 else 'Empeoró'}"
        )
        st.metric("Volatilidad del Sentimiento", f"{volatility:.2f}")
    with col2:
        success_text = "✅ Exitosa" if metrics['call_success'] else "⚠️ Requiere Atención"
        st.metric("Estado de Llamada", success_text)
        st.metric("Total Segmentos", metrics['total_segments'])
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("% Positivo", f"{time_in_sentiment['positive']:.1f}%")
    with col4:
        st.metric("% Neutral", f"{time_in_sentiment['neutral']:.1f}%")
    with col5:
        st.metric("% Negativo", f"{time_in_sentiment['negative']:.1f}%")
    accuracy = (metrics['successful_analyses'] / metrics['total_segments']) * 100
    st.metric("Precisión", f"{accuracy:.1f}%")
    outcome_mapping = {
        'highly_successful': '🎉 Muy Exitosa',
        'successful': '✅ Exitosa', 
        'neutral': '➡️ Neutral',
        'needs_attention': '⚠️ Requiere Atención'
    }
    outcome_text = outcome_mapping.get(summary['call_outcome'], summary['call_outcome'])
    st.info(f"**Resultado:** {outcome_text}")
    if results.get('recommendations'):
        st.subheader("💡 Recomendaciones")
        for rec in results['recommendations']:
            st.write(f"• {rec}")
    st.subheader("📈 Análisis Visual")
    create_timeline_chart(results)
    # Time spent in each sentiment bar chart
    st.subheader("⏳ Tiempo en Cada Sentimiento (Cliente)")
    fig = go.Figure(data=[
        go.Bar(
            x=list(time_in_sentiment.keys()),
            y=list(time_in_sentiment.values()),
            marker_color=['#28a745', '#ffc107', '#dc3545']
        )
    ])
    fig.update_layout(
        title="Proporción de Tiempo en Cada Sentimiento (Cliente)",
        xaxis_title="Sentimiento",
        yaxis_title="% del Tiempo",
        yaxis_range=[0, 100],
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("📋 Resultados Detallados")
    show_detailed_table(results)
    st.subheader("💾 Exportar")
    show_export_options(results)

def create_timeline_chart(results):
    """Create sentiment timeline chart (customer only)"""
    timeline_data = []
    for segment in results['analyzed_segments']:
        if segment['speaker'].lower() in ['customer', 'cliente', 'client']:
            numeric_score = {'positive': 1, 'neutral': 0, 'negative': -1}[segment['sentiment']]
            weighted_score = numeric_score * segment['intensity']
            timeline_data.append({
                'timestamp': segment['timestamp'],
                'sentiment_score': weighted_score,
                'sentiment': segment['sentiment'],
                'text': segment['original_text'][:50] + '...' if len(segment['original_text']) > 50 else segment['original_text']
            })
    df = pd.DataFrame(timeline_data)
    fig = px.line(
        df,
        x='timestamp',
        y='sentiment_score',
        title="Evolución del Sentimiento del Cliente Durante la Llamada",
        hover_data=['sentiment', 'text'],
        markers=True,
        height=400
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        xaxis_title="Tiempo",
        yaxis_title="Puntuación de Sentimiento"
    )
    st.plotly_chart(fig, use_container_width=True)

def create_sentiment_pie(results):
    """Create sentiment distribution pie chart"""
    
    sentiment_dist = results['summary']['sentiment_distribution']
    colors = ['#28a745', '#ffc107', '#dc3545']  # green, yellow, red
    
    fig = px.pie(
        values=list(sentiment_dist.values()),
        names=list(sentiment_dist.keys()),
        title="Distribución de Sentimientos",
        color_discrete_sequence=colors
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_detailed_table(results):
    """Show detailed results table with colors (customer only)"""
    table_data = []
    for segment in results['analyzed_segments']:
        if segment['speaker'].lower() in ['customer', 'cliente', 'client']:
            table_data.append({
                'Timestamp': segment['timestamp'],
                'Text': segment['original_text'][:100] + '...' if len(segment['original_text']) > 100 else segment['original_text'],
                'Sentiment': segment['sentiment'],
                'Intensity': segment['intensity'],
                'Context': segment['context']
            })
    df = pd.DataFrame(table_data)
    def highlight_sentiment(val):
        if val == 'positive':
            return 'background-color: #d1f2d9; color: #155724; font-weight: bold'
        elif val == 'negative':
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
        elif val == 'neutral':
            return 'background-color: #fff3b8; color: #856404; font-weight: bold'
        return ''
    styled_df = df.style.applymap(highlight_sentiment, subset=['Sentiment'])
    st.dataframe(styled_df, use_container_width=True)

def show_export_options(results):
    """Show export download buttons"""
    
    # Prepare export data
    export_data = {
        'metadata': {
            'call_id': results['call_id'],
            'timestamp': results['timestamp'],
            'summary': results['summary']
        },
        'metrics': results['metrics'],
        'segments': []
    }
    
    for segment in results['analyzed_segments']:
        export_data['segments'].append({
            'timestamp': segment['timestamp'],
            'speaker': segment['speaker'],
            'text': segment['original_text'],
            'sentiment': segment['sentiment'],
            'intensity': segment['intensity'],
            'context': segment['context']
        })
    
    # Create filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"sabadell_analysis_{timestamp}"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # JSON export
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        st.download_button(
            "📥 Descargar JSON",
            json_data,
            file_name=f"{filename_base}.json",
            mime="application/json"
        )
    
    with col2:
        # CSV export
        csv_df = pd.DataFrame(export_data['segments'])
        csv_data = csv_df.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"{filename_base}.csv",
            mime="text/csv"
        )
    
    with col3:
        # Summary report
        report = f"""
BANCO SABADELL - ANÁLISIS DE SENTIMIENTOS
========================================

ID: {results['call_id']}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

MÉTRICAS:
- Mejora Cliente: {results['metrics']['customer_improvement']:+.2f}
- Llamada Exitosa: {'Sí' if results['metrics']['call_success'] else 'No'}
- Total Segmentos: {results['metrics']['total_segments']}

RESULTADO: {results['summary']['call_outcome'].upper()}

DISTRIBUCIÓN:
- Positivos: {results['summary']['sentiment_distribution']['positive']}
- Neutrales: {results['summary']['sentiment_distribution']['neutral']}
- Negativos: {results['summary']['sentiment_distribution']['negative']}
"""
        
        st.download_button(
            "📥 Reporte",
            report,
            file_name=f"{filename_base}_report.txt",
            mime="text/plain"
        )
    
    # Footer
    st.divider()
    st.markdown("""
    ---
    **🏦 Banco Sabadell - Análisis de Sentimientos**  
    *ESADE Capstone Project 2025 | Powered by Cohere AI + AssemblyAI*
    """)

if __name__ == "__main__":
    main()