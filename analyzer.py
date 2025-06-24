# analyzer.py - Core sentiment analysis functionality

import cohere
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import streamlit as st
from config import COHERE_SETTINGS, SENTIMENT_CONFIG, DEFAULT_PROMPTS

class SabadellSentimentAnalyzer:
    """
    Core sentiment analysis class for Banco Sabadell call center conversations
    """
    
    def __init__(self, api_key: str):
        """Initialize the analyzer with Cohere API key"""
        try:
            self.co = cohere.Client(api_key)
            self.api_connected = True
            self.settings = COHERE_SETTINGS
            self.sentiment_config = SENTIMENT_CONFIG
        except Exception as e:
            self.api_connected = False
            st.error(f"Error connecting to Cohere API: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test if Cohere API is working properly"""
        if not self.api_connected:
            return False
            
        try:
            response = self.co.chat(
                model=self.settings["model"],
                message="Test connection",
                max_tokens=10
            )
            return True
        except Exception as e:
            st.error(f"API Connection failed: {str(e)}")
            return False
    
    def analyze_call_segment(self, segment: Dict[str, Any], custom_prompt: str = None) -> Dict[str, Any]:
        """
        Analyze a single call segment for sentiment using Cohere
        
        Args:
            segment: Dictionary with 'speaker', 'text', and optional 'timestamp'
            custom_prompt: Optional custom prompt template
            
        Returns:
            Dictionary with sentiment analysis results
        """
        
        if not self.api_connected:
            return self._create_error_response(segment, "API not connected")
        
        # Select prompt
        if custom_prompt:
            prompt = custom_prompt.format(
                speaker=segment['speaker'],
                text=segment['text'],
                timestamp=segment.get('timestamp', 'N/A')
            )
        else:
            prompt = DEFAULT_PROMPTS["spanish_banking"].format(
                speaker=segment['speaker'],
                text=segment['text'],
                timestamp=segment.get('timestamp', 'N/A')
            )
        
        try:
            response = self.co.chat(
                model=self.settings["model"],
                message=prompt,
                temperature=self.settings["temperature"],
                max_tokens=self.settings["max_tokens"]
            )
            
            return self._parse_cohere_response(response.text, segment)
            
        except Exception as e:
            st.error(f"Error analyzing segment: {str(e)}")
            return self._create_error_response(segment, str(e))
    
    def _parse_cohere_response(self, response_text: str, original_segment: Dict) -> Dict[str, Any]:
        """Parse Cohere's response into structured data"""
        
        lines = response_text.strip().split('\n')
        result = {
            'timestamp': original_segment.get('timestamp', 'N/A'),
            'speaker': original_segment['speaker'],
            'original_text': original_segment['text'],
            'sentiment': 'neutral',  # default
            'intensity': 3,          # default
            'context': '',
            'raw_response': response_text,
            'analysis_status': 'success'
        }
        
        # Parse response lines
        for line in lines:
            line = line.strip()
            
            if line.startswith('Sentimiento:') or line.startswith('Sentiment:'):
                sentiment_text = line.split(':', 1)[1].strip().lower()
                if any(word in sentiment_text for word in ['positivo', 'positive']):
                    result['sentiment'] = 'positive'
                elif any(word in sentiment_text for word in ['negativo', 'negative']):
                    result['sentiment'] = 'negative'
                else:
                    result['sentiment'] = 'neutral'
                    
            elif line.startswith('Intensidad:') or line.startswith('Intensity:'):
                try:
                    intensity_str = line.split(':', 1)[1].strip()
                    # Extract first digit found
                    intensity_match = re.search(r'(\d)', intensity_str)
                    if intensity_match:
                        intensity = int(intensity_match.group(1))
                        result['intensity'] = max(1, min(5, intensity))  # Clamp between 1-5
                except Exception:
                    result['intensity'] = 3  # default
                    
            elif line.startswith('Contexto:') or line.startswith('Context:'):
                result['context'] = line.split(':', 1)[1].strip()
        
        return result
    
    def _create_error_response(self, segment: Dict, error_msg: str = "Analysis error") -> Dict[str, Any]:
        """Create default response for errors"""
        return {
            'timestamp': segment.get('timestamp', 'N/A'),
            'speaker': segment['speaker'],
            'original_text': segment['text'],
            'sentiment': 'neutral',
            'intensity': 3,
            'context': f'Error: {error_msg}',
            'raw_response': f'ERROR: {error_msg}',
            'analysis_status': 'error'
        }
    
    def analyze_full_call(self, call_segments: List[Dict[str, Any]], custom_prompt: str = None) -> Dict[str, Any]:
        """
        Analyze complete call and calculate improvement indicator
        
        Args:
            call_segments: List of conversation segments
            custom_prompt: Optional custom prompt template
            
        Returns:
            Complete analysis results with improvement indicators
        """
        
        if not call_segments:
            raise ValueError("No call segments provided")
        
        # Progress tracking
        analyzed_segments = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, segment in enumerate(call_segments):
            status_text.text(f"Analyzing segment {i+1}/{len(call_segments)}: {segment['speaker']}")
            analysis = self.analyze_call_segment(segment, custom_prompt)
            analyzed_segments.append(analysis)
            progress_bar.progress((i + 1) / len(call_segments))
        
        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Separate by speaker type
        customer_segments = self._filter_by_speaker_type(analyzed_segments, 'customer')
        # Remove agent_segments and agent_improvement
        # Calculate improvement metrics
        customer_improvement = self._calculate_improvement(customer_segments)
        overall_improvement = self._calculate_overall_improvement(analyzed_segments)
        # Determine call success
        call_success = customer_improvement > 0
        # Generate comprehensive results
        return {
            'call_id': f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'analyzed_segments': analyzed_segments,
            'customer_trajectory': customer_segments,
            'metrics': {
                'customer_improvement': customer_improvement,
                'overall_improvement': overall_improvement,
                'call_success': call_success,
                'total_segments': len(analyzed_segments),
                'successful_analyses': len([s for s in analyzed_segments if s['analysis_status'] == 'success']),
                'error_count': len([s for s in analyzed_segments if s['analysis_status'] == 'error'])
            },
            'summary': self._generate_call_summary(analyzed_segments, customer_improvement),
            'recommendations': self._generate_recommendations(customer_improvement)
        }
    
    def _filter_by_speaker_type(self, segments: List[Dict], speaker_type: str) -> List[Dict]:
        """Filter segments by speaker type (customer or agent)"""
        aliases = self.sentiment_config['speaker_aliases'][speaker_type]
        return [s for s in segments if s['speaker'].lower() in aliases]
    
    def _calculate_improvement(self, segments: List[Dict]) -> float:
        """Calculate improvement score from beginning to end of conversation"""
        if len(segments) < 2:
            return 0.0
        
        sentiment_values = self.sentiment_config['sentiment_values']
        
        # Get first and last segments
        first_segment = segments[0]
        last_segment = segments[-1]
        
        # Calculate weighted scores (sentiment * intensity)
        initial_score = sentiment_values[first_segment['sentiment']] * first_segment['intensity']
        final_score = sentiment_values[last_segment['sentiment']] * last_segment['intensity']
        
        return final_score - initial_score
    
    def _calculate_overall_improvement(self, segments: List[Dict]) -> float:
        """Calculate overall conversation improvement"""
        if len(segments) < 4:  # Need minimum segments for trend analysis
            return 0.0
        
        sentiment_values = self.sentiment_config['sentiment_values']
        
        # Calculate average sentiment in first and second half
        midpoint = len(segments) // 2
        first_half = segments[:midpoint]
        second_half = segments[midpoint:]
        
        first_half_avg = sum(sentiment_values[s['sentiment']] * s['intensity'] for s in first_half) / len(first_half)
        second_half_avg = sum(sentiment_values[s['sentiment']] * s['intensity'] for s in second_half) / len(second_half)
        
        return second_half_avg - first_half_avg
    
    def _generate_call_summary(self, segments: List[Dict], improvement: float) -> Dict[str, Any]:
        """Generate comprehensive call summary"""
        
        # Count sentiments
        sentiment_counts = {
            'positive': len([s for s in segments if s['sentiment'] == 'positive']),
            'neutral': len([s for s in segments if s['sentiment'] == 'neutral']),
            'negative': len([s for s in segments if s['sentiment'] == 'negative'])
        }
        
        # Calculate average intensity
        avg_intensity = sum(s['intensity'] for s in segments) / len(segments) if segments else 0
        
        # Determine call outcome
        if improvement > 2:
            outcome = 'highly_successful'
        elif improvement > 0:
            outcome = 'successful'
        elif improvement > -2:
            outcome = 'neutral'
        else:
            outcome = 'needs_attention'
        
        return {
            'improvement_score': round(improvement, 2),
            'sentiment_distribution': sentiment_counts,
            'average_intensity': round(avg_intensity, 2),
            'call_outcome': outcome,
            'dominant_sentiment': max(sentiment_counts, key=sentiment_counts.get),
            'total_exchanges': len(segments)
        }
    
    def _generate_recommendations(self, customer_improvement: float) -> List[str]:
        """Generate actionable recommendations based on customer improvement only"""
        recommendations = []
        if customer_improvement > 1:
            recommendations.append("✅ Excellent customer experience - call resolved successfully")
        elif customer_improvement > 0:
            recommendations.append("✅ Customer sentiment improved during the call")
        elif customer_improvement < -1:
            recommendations.append("⚠️ Customer satisfaction declined - follow-up recommended")
        else:
            recommendations.append("➡️ Customer sentiment remained stable")
        if customer_improvement < 0:
            recommendations.append("📞 Consider proactive follow-up call")
        return recommendations
    
# Call Solution Analysis
    def analyze_call_solution(self, transcribed_text: str, custom_prompt: Optional[str] = None) -> int:
        """
        Analyze the customer service call transcript using Cohere to determine if the customer's issue was resolved.
        Return 1 if resolved, 0 otherwise.
        """
        if not self.api_connected:
            st.error("Cohere API is not connected")
            return 0

        if custom_prompt:
            prompt = custom_prompt.format(transcribed_text=transcribed_text)
        else:
            prompt = (
                "Analyze the following customer service call transcript and determine if the customer's issue was resolved during the call. "
                "Return ONLY a JSON object with a single key 'solved' set to 1 if the problem was resolved, or 0 if not resolved. Do not include any extra text.\n\n"
                "Transcript:\n" + transcribed_text
            )

        try:
            response = self.co.chat(
                model=self.settings["model"],
                message=prompt,
                temperature=self.settings["temperature"],
                max_tokens=self.settings["max_tokens"]
            )
            response_text = response.text.strip()

            if not response_text:
                st.error("DEBUG: Received empty response from Cohere.")
                return 0

            answer_data = json.loads(response_text)
            solved_value = answer_data.get("solved", 0)
            return int(solved_value)
        except Exception as e:
            st.error(f"Error analyzing call solution: {str(e)}")
            return 0