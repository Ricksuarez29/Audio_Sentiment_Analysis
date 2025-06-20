# utils.py - Utility functions for data parsing and visualization

import json
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any, Optional
import streamlit as st
from config import VIZ_CONFIG, EXPORT_CONFIG

class ConversationParser:
    """Parser for different conversation formats"""
    
    @staticmethod
    def parse_conversation_text(text: str, format_type: str) -> List[Dict[str, Any]]:
        """
        Parse conversation text into segments based on format type
        
        Args:
            text: Raw conversation text
            format_type: One of "Simple Format", "Timestamped Format", "JSON Format"
            
        Returns:
            List of conversation segments
        """
        
        segments = []
        text = text.strip()
        
        if not text:
            return segments
        
        try:
            if format_type == "Simple Format":
                segments = ConversationParser._parse_simple_format(text)
            elif format_type == "Timestamped Format":
                segments = ConversationParser._parse_timestamped_format(text)
            elif format_type == "JSON Format":
                segments = ConversationParser._parse_json_format(text)
            else:
                st.error(f"Unknown format type: {format_type}")
                
        except Exception as e:
            st.error(f"Error parsing conversation: {str(e)}")
            
        return segments
    
    @staticmethod
    def _parse_simple_format(text: str) -> List[Dict[str, Any]]:
        """Parse simple 'Speaker: Text' format"""
        segments = []
        lines = text.strip().split('\n')
        timestamp_counter = 0
        
        for line in lines:
            line = line.strip()
            if ':' in line and line:
                try:
                    speaker, text_content = line.split(':', 1)
                    speaker = speaker.strip()
                    text_content = text_content.strip()
                    
                    if speaker and text_content:  # Both must be non-empty
                        segments.append({
                            'speaker': speaker,
                            'text': text_content,
                            'timestamp': f"{timestamp_counter//2:02d}:{(timestamp_counter%2)*30:02d}"
                        })
                        timestamp_counter += 1
                        
                except ValueError:
                    continue  # Skip malformed lines
                    
        return segments
    
    @staticmethod
    def _parse_timestamped_format(text: str) -> List[Dict[str, Any]]:
        """Parse '[HH:MM] Speaker: Text' format"""
        segments = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Match timestamp pattern: [HH:MM] or [MM:SS]
            timestamp_pattern = r'\[(\d{1,2}:\d{2})\]\s*(.+)'
            timestamp_match = re.match(timestamp_pattern, line)
            
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                content = timestamp_match.group(2).strip()
                
                if ':' in content:
                    try:
                        speaker, text_content = content.split(':', 1)
                        speaker = speaker.strip()
                        text_content = text_content.strip()
                        
                        if speaker and text_content:
                            segments.append({
                                'speaker': speaker,
                                'text': text_content,
                                'timestamp': timestamp
                            })
                            
                    except ValueError:
                        continue
                        
        return segments
    
    @staticmethod
    def _parse_json_format(text: str) -> List[Dict[str, Any]]:
        """Parse JSON array format"""
        try:
            data = json.loads(text)
            
            if not isinstance(data, list):
                st.error("JSON should be an array of conversation segments")
                return []
            
            segments = []
            for item in data:
                if isinstance(item, dict) and 'speaker' in item and 'text' in item:
                    # Ensure required fields exist
                    segment = {
                        'speaker': str(item['speaker']).strip(),
                        'text': str(item['text']).strip(),
                        'timestamp': item.get('timestamp', 'N/A')
                    }
                    
                    if segment['speaker'] and segment['text']:
                        segments.append(segment)
                        
            return segments
            
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {str(e)}")
            return []
    
    @staticmethod
    def validate_segments(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate parsed segments and return validation results
        
        Returns:
            Dictionary with validation results and statistics
        """
        
        if not segments:
            return {
                'valid': False,
                'error': 'No valid segments found',
                'stats': {}
            }
        
        # Count speakers
        speakers = set(seg['speaker'] for seg in segments)
        speaker_counts = {speaker: sum(1 for seg in segments if seg['speaker'] == speaker) 
                         for speaker in speakers}
        
        # Check for minimum viable conversation
        if len(segments) < 2:
            return {
                'valid': False,
                'error': 'Conversation too short (minimum 2 segments required)',
                'stats': {'total_segments': len(segments), 'speakers': list(speakers)}
            }
        
        # Check for dialogue (at least 2 different speakers)
        if len(speakers) < 2:
            return {
                'valid': False,
                'error': 'Conversation needs at least 2 different speakers',
                'stats': {'total_segments': len(segments), 'speakers': list(speakers)}
            }
        
        return {
            'valid': True,
            'stats': {
                'total_segments': len(segments),
                'speakers': list(speakers),
                'speaker_counts': speaker_counts,
                'avg_text_length': sum(len(seg['text']) for seg in segments) / len(segments)
            }
        }

class VisualizationManager:
    """Manager for creating visualizations from analysis results"""
    
    @staticmethod
    def create_customer_timeline(results: Dict[str, Any]) -> go.Figure:
        """Create customer sentiment timeline"""
        
        # Filter customer data
        customer_data = []
        for segment in results['analyzed_segments']:
            speaker_lower = segment['speaker'].lower()
            if speaker_lower in ['customer', 'cliente', 'client']:
                numeric_score = {'positive': 1, 'neutral': 0, 'negative': -1}[segment['sentiment']]
                weighted_score = numeric_score * segment['intensity']
                
                customer_data.append({
                    'timestamp': segment['timestamp'],
                    'sentiment_score': weighted_score,
                    'text': segment['original_text'][:50] + '...' if len(segment['original_text']) > 50 else segment['original_text']
                })
        
        if not customer_data:
            # Return empty figure if no customer data
            fig = go.Figure()
            fig.update_layout(title="📞 Cliente - Sin datos disponibles")
            return fig
        
        df = pd.DataFrame(customer_data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['sentiment_score'],
            mode='lines+markers',
            name='Cliente',
            line=dict(color='#FF6B6B', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            title="📞 Evolución del Sentimiento - Cliente",
            xaxis_title="Tiempo",
            yaxis_title="Puntuación",
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_agent_timeline(results: Dict[str, Any]) -> go.Figure:
        """Create agent sentiment timeline"""
        
        # Filter agent data
        agent_data = []
        for segment in results['analyzed_segments']:
            speaker_lower = segment['speaker'].lower()
            if speaker_lower in ['agent', 'agente', 'operador', 'gestor']:
                numeric_score = {'positive': 1, 'neutral': 0, 'negative': -1}[segment['sentiment']]
                weighted_score = numeric_score * segment['intensity']
                
                agent_data.append({
                    'timestamp': segment['timestamp'],
                    'sentiment_score': weighted_score,
                    'text': segment['original_text'][:50] + '...' if len(segment['original_text']) > 50 else segment['original_text']
                })
        
        if not agent_data:
            # Return empty figure if no agent data
            fig = go.Figure()
            fig.update_layout(title="👤 Agente - Sin datos disponibles")
            return fig
        
        df = pd.DataFrame(agent_data)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['sentiment_score'],
            mode='lines+markers',
            name='Agente',
            line=dict(color='#4ECDC4', width=3),
            marker=dict(size=8)
        ))
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            title="👤 Evolución del Sentimiento - Agente",
            xaxis_title="Tiempo",
            yaxis_title="Puntuación",
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_sentiment_distribution(results: Dict[str, Any]) -> go.Figure:
        """Create sentiment distribution pie chart"""
        
        sentiment_dist = results['summary']['sentiment_distribution']
        
        fig = px.pie(
            values=list(sentiment_dist.values()),
            names=list(sentiment_dist.keys()),
            title="Distribución de Sentimientos",
            color_discrete_map=VIZ_CONFIG['colors'],
            height=VIZ_CONFIG['chart_height']
        )
        
        # Customize pie chart
        fig.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        )
        
        return fig
    
    @staticmethod
    def create_speaker_comparison(results: Dict[str, Any]) -> go.Figure:
        """Create speaker sentiment comparison"""
        
        customer_segments = results.get('customer_trajectory', [])
        agent_segments = results.get('agent_trajectory', [])
        
        # Calculate average sentiments
        def calc_avg_sentiment(segments):
            if not segments:
                return 0
            sentiment_values = {'negative': -1, 'neutral': 0, 'positive': 1}
            return sum(sentiment_values[s['sentiment']] * s['intensity'] for s in segments) / len(segments)
        
        customer_avg = calc_avg_sentiment(customer_segments)
        agent_avg = calc_avg_sentiment(agent_segments)
        
        fig = go.Figure(data=[
            go.Bar(
                x=['Cliente', 'Agente'],
                y=[customer_avg, agent_avg],
                marker_color=['#FF6B6B' if customer_avg < 0 else '#4ECDC4', 
                             '#FF6B6B' if agent_avg < 0 else '#4ECDC4'],
                text=[f'{customer_avg:.2f}', f'{agent_avg:.2f}'],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title="Comparación de Sentimiento Promedio por Hablante",
            yaxis_title="Sentimiento Promedio",
            height=VIZ_CONFIG['chart_height']
        )
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        return fig

class ExportManager:
    """Manager for exporting analysis results"""
    
    @staticmethod
    def prepare_results_for_export(results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare results for clean export"""
        
        # Create clean export version
        export_data = {
            'metadata': {
                'call_id': results['call_id'],
                'timestamp': results['timestamp'],
                'analysis_summary': results['summary']
            },
            'metrics': results['metrics'],
            'segments': []
        }
        
        # Clean up segments for export
        for segment in results['analyzed_segments']:
            clean_segment = {
                'timestamp': segment['timestamp'],
                'speaker': segment['speaker'],
                'text': segment['original_text'],
                'sentiment': segment['sentiment'],
                'intensity': segment['intensity'],
                'context': segment['context'],
                'status': segment['analysis_status']
            }
            export_data['segments'].append(clean_segment)
        
        return export_data
    
    @staticmethod
    def create_export_dataframe(results: Dict[str, Any]) -> pd.DataFrame:
        """Create pandas DataFrame for CSV export"""
        
        df_data = []
        for segment in results['analyzed_segments']:
            df_data.append({
                'Timestamp': segment['timestamp'],
                'Speaker': segment['speaker'],
                'Text': segment['original_text'],
                'Sentiment': segment['sentiment'],
                'Intensity': segment['intensity'],
                'Context': segment['context'],
                'Status': segment['analysis_status']
            })
        
        return pd.DataFrame(df_data)
    
    @staticmethod
    def generate_export_filename(prefix: str = "sabadell_analysis") -> str:
        """Generate timestamped filename for exports"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return EXPORT_CONFIG['filename_format'].format(timestamp=timestamp)

class FormatExamples:
    """Static examples for different input formats"""
    
    SIMPLE_FORMAT = """Customer: Estoy muy molesto con el servicio de mi tarjeta
Agent: Entiendo su frustración, permítame ayudarle
Customer: Mi tarjeta no funciona desde hace días
Agent: Voy a revisar su cuenta inmediatamente
Customer: Gracias, espero que puedan solucionarlo
Agent: He reactivado su tarjeta, ya debería funcionar
Customer: Perfecto, muchas gracias por la ayuda rápida"""
    
    TIMESTAMPED_FORMAT = """[00:30] Customer: Estoy muy molesto con el servicio
[01:00] Agent: Entiendo su frustración, vamos a solucionarlo
[01:30] Customer: Mi tarjeta no funciona desde hace días
[02:00] Agent: Voy a revisar su cuenta ahora mismo
[02:30] Customer: Gracias por la ayuda
[03:00] Agent: He reactivado su tarjeta correctamente
[03:30] Customer: Perfecto, muchas gracias"""
    
    JSON_FORMAT = """[
  {"speaker": "Customer", "text": "Estoy muy molesto con el servicio", "timestamp": "00:30"},
  {"speaker": "Agent", "text": "Entiendo su frustración", "timestamp": "01:00"},
  {"speaker": "Customer", "text": "Mi tarjeta no funciona", "timestamp": "01:30"},
  {"speaker": "Agent", "text": "Voy a revisar su cuenta", "timestamp": "02:00"},
  {"speaker": "Customer", "text": "Gracias por la ayuda", "timestamp": "02:30"},
  {"speaker": "Agent", "text": "He reactivado su tarjeta", "timestamp": "03:00"},
  {"speaker": "Customer", "text": "Perfecto, muchas gracias", "timestamp": "03:30"}
]"""
    
    @classmethod
    def get_example(cls, format_type: str) -> str:
        """Get example for specific format type"""
        examples = {
            "Simple Format": cls.SIMPLE_FORMAT,
            "Timestamped Format": cls.TIMESTAMPED_FORMAT,
            "JSON Format": cls.JSON_FORMAT
        }
        return examples.get(format_type, cls.SIMPLE_FORMAT)