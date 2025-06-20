# config.py - Configuration settings for Banco Sabadell Sentiment Analysis

# Cohere API Configuration
COHERE_API_KEY = "E63EAO5eXn2wSr5HgsK1spAtsT4YqhjV6wvXvtUA"  # Replace with your actual API key

# AssemblyAI API Configuration
ASSEMBLYAI_API_KEY = "9613e47d0f17402a9b9b2d38c3d60a22"  # Replace with your actual API key

# App Configuration
APP_CONFIG = {
    "page_title": "Banco Sabadell - Análisis de Sentimientos",
    "page_icon": "🏦",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Cohere Model Settings
COHERE_SETTINGS = {
    "model": "command-r",
    "temperature": 0.1,
    "max_tokens": 200
}

# AssemblyAI Settings
ASSEMBLYAI_SETTINGS = {
    "language_code": "es",          # Default to Spanish
    "speaker_labels": True,         # Enable speaker diarization
    "speakers_expected": 2,         # Customer + Agent
    "punctuate": True,             # Add punctuation
    "format_text": True,           # Format text nicely
    "dual_channel": False          # Set to True for stereo recordings
}

# Sentiment Analysis Configuration
SENTIMENT_CONFIG = {
    "sentiment_values": {
        "negative": -1,
        "neutral": 0,
        "positive": 1
    },
    "speaker_aliases": {
        "customer": ["customer", "cliente", "client"],
        "agent": ["agent", "agente", "operador", "gestor"]
    }
}

# Default Prompts
DEFAULT_PROMPTS = {
    "spanish_banking": """
    Eres un analista de sentimientos especializado en llamadas bancarias en español.
    
    Analiza el siguiente segmento de una llamada bancaria:
    
    Hablante: {speaker}
    Texto: "{text}"
    Momento: {timestamp}
    
    Proporciona EXACTAMENTE en este formato:
    Sentimiento: [Positivo/Neutral/Negativo]
    Intensidad: [1-5] (1=muy bajo, 5=muy alto)
    Contexto: [breve explicación del contexto bancario]
    """,
    
    "general": """
    Analyze this conversation segment for sentiment:
    Speaker: {speaker}
    Text: "{text}"
    Timestamp: {timestamp}
    
    Provide in this exact format:
    Sentiment: [Positive/Neutral/Negative]
    Intensity: [1-5] (1=very low, 5=very high)
    Context: [brief explanation]
    """
}

# File Upload Settings
UPLOAD_CONFIG = {
    "allowed_text_extensions": ['txt', 'json'],
    "allowed_audio_extensions": ['mp3', 'wav', 'mp4', 'm4a', 'flac', 'ogg'],
    "max_file_size_mb": 25,        # Increased for audio files
    "encoding": "utf-8"
}

# Visualization Settings
VIZ_CONFIG = {
    "colors": {
        "positive": "#28a745",    # Vivid green
        "neutral": "#ffc107",     # Vivid yellow/orange
        "negative": "#dc3545"     # Vivid red
    },
    "chart_height": 400,
    "table_colors": {
        "positive": "#d1f2d9",    # Light vivid green background
        "neutral": "#fff3b8",     # Light vivid yellow background  
        "negative": "#f8d7da"     # Light vivid red background
    }
}

# Export Settings
EXPORT_CONFIG = {
    "json_indent": 2,
    "csv_index": False,
    "filename_format": "sabadell_analysis_{timestamp}"
}