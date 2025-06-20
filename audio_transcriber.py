# audio_transcriber.py - Audio Transcription Module using AssemblyAI

import requests
import streamlit as st
import time
from typing import Dict, List, Any, Optional
import tempfile
import os

class AudioTranscriber:
    """Audio transcription with speaker diarization using AssemblyAI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.assemblyai.com/v2"
        self.headers = {"authorization": api_key}
    
    def test_connection(self) -> bool:
        """Test if AssemblyAI API key is working"""
        try:
            response = requests.get(
                f"{self.base_url}/transcript",
                headers=self.headers
            )
            return response.status_code in [200, 400]  # 400 is expected for GET without params
        except Exception as e:
            st.error(f"Connection test failed: {str(e)}")
            return False
    
    def transcribe_audio(self, uploaded_file, language: str = "es") -> Dict[str, Any]:
        """
        Transcribe audio file with speaker diarization
        
        Args:
            uploaded_file: Streamlit uploaded file object
            language: Language code (es for Spanish, en for English)
            
        Returns:
            Dictionary with transcription results
        """
        
        # Step 1: Save uploaded file temporarily
        temp_file_path = self._save_uploaded_file(uploaded_file)
        if not temp_file_path:
            return {"error": "Failed to save uploaded file"}
        
        try:
            # Step 2: Upload audio file to AssemblyAI
            upload_url = self._upload_file(temp_file_path)
            if not upload_url:
                return {"error": "Failed to upload audio file to AssemblyAI"}
            
            # Step 3: Request transcription with speaker diarization
            transcript_response = self._request_transcription(upload_url, language)
            if not transcript_response:
                return {"error": "Failed to request transcription"}
            
            # Step 4: Poll for completion
            transcript_id = transcript_response["id"]
            final_transcript = self._poll_transcription(transcript_id)
            
            if final_transcript.get("status") == "completed":
                return self._format_conversation(final_transcript)
            else:
                error_msg = final_transcript.get("error", "Unknown error")
                return {"error": f"Transcription failed: {error_msg}"}
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    def _save_uploaded_file(self, uploaded_file) -> Optional[str]:
        """Save Streamlit uploaded file to temporary location"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                return tmp_file.name
        except Exception as e:
            st.error(f"Error saving uploaded file: {str(e)}")
            return None
    
    def _upload_file(self, file_path: str) -> Optional[str]:
        """Upload audio file to AssemblyAI"""
        
        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    f"{self.base_url}/upload",
                    headers=self.headers,
                    files={"file": f}
                )
            
            if response.status_code == 200:
                return response.json()["upload_url"]
            else:
                st.error(f"Upload failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Error uploading file: {str(e)}")
            return None
    
    def _request_transcription(self, audio_url: str, language: str) -> Optional[Dict]:
        """Request transcription with speaker diarization"""
        
        config = {
            "audio_url": audio_url,
            "language_code": language,
            "speaker_labels": True,  # Enable speaker diarization
            "speakers_expected": 2,  # Expect 2 speakers (customer + agent)
            "punctuate": True,
            "format_text": True,
            "dual_channel": False,  # Set to True if stereo with separate channels
            "boost_param": "default"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/transcript",
                headers=self.headers,
                json=config
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Transcription request failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            st.error(f"Error requesting transcription: {str(e)}")
            return None
    
    def _poll_transcription(self, transcript_id: str) -> Dict:
        """Poll transcription status until completion"""
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        poll_count = 0
        max_polls = 60  # Maximum 3 minutes of polling (60 * 3 seconds)
        
        while poll_count < max_polls:
            try:
                response = requests.get(
                    f"{self.base_url}/transcript/{transcript_id}",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    progress_bar.empty()
                    status_text.empty()
                    return {"error": f"Polling failed with status {response.status_code}"}
                
                result = response.json()
                status = result.get("status")
                
                if status == "completed":
                    progress_bar.progress(100)
                    status_text.text("✅ Transcription completed!")
                    time.sleep(1)
                    progress_bar.empty()
                    status_text.empty()
                    return result
                
                elif status == "error":
                    progress_bar.empty()
                    status_text.empty()
                    return result
                
                else:
                    # Still processing
                    progress_percentage = min(poll_count * 5, 90)  # Show progress up to 90%
                    status_text.text(f"🔄 Transcribing audio... Status: {status}")
                    progress_bar.progress(progress_percentage)
                    time.sleep(3)  # Wait 3 seconds before next poll
                    poll_count += 1
                    
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                return {"error": f"Polling error: {str(e)}"}
        
        # Timeout
        progress_bar.empty()
        status_text.empty()
        return {"error": "Transcription timeout - please try again with a shorter audio file"}
    
    def _format_conversation(self, transcript_data: Dict) -> Dict[str, Any]:
        """Format AssemblyAI output into conversation format"""
        
        if "utterances" not in transcript_data:
            return {"error": "No speaker information found in transcript"}
        
        utterances = transcript_data["utterances"]
        if not utterances:
            return {"error": "No speech detected in audio"}
        
        conversation_segments = []
        
        for i, utterance in enumerate(utterances):
            speaker_label = utterance["speaker"]
            text = utterance["text"].strip()
            start_time = utterance["start"]  # milliseconds
            confidence = utterance.get("confidence", 0.0)
            
            # Convert milliseconds to MM:SS format
            minutes = int(start_time // 60000)
            seconds = int((start_time % 60000) // 1000)
            timestamp = f"{minutes:02d}:{seconds:02d}"
            
            # Determine speaker name based on patterns or simple alternating
            if i == 0:
                # First speaker is typically the agent
                speaker_name = "Agent"
            else:
                # Alternate speakers or use simple logic
                prev_speaker = conversation_segments[-1]["speaker"]
                speaker_name = "Customer" if prev_speaker == "Agent" else "Agent"
            
            # Override with customer/agent detection if possible
            if any(word in text.lower() for word in ["buenos días", "buenas tardes", "¿en qué puedo ayudarle?", "banco sabadell"]):
                speaker_name = "Agent"
            elif any(word in text.lower() for word in ["tengo un problema", "necesito ayuda", "estoy molesto"]):
                speaker_name = "Customer"
            
            conversation_segments.append({
                "speaker": speaker_name,
                "text": text,
                "timestamp": timestamp,
                "confidence": confidence,
                "original_speaker": speaker_label
            })
        
        # Format as simple text for your app
        formatted_conversation = "\n".join([
            f"{seg['speaker']}: {seg['text']}"
            for seg in conversation_segments
        ])
        
        return {
            "success": True,
            "formatted_conversation": formatted_conversation,
            "segments": conversation_segments,
            "full_transcript": transcript_data.get("text", ""),
            "confidence": transcript_data.get("confidence", 0.0),
            "language_detected": transcript_data.get("language_code", "unknown"),
            "audio_duration": transcript_data.get("audio_duration", 0) / 1000,  # Convert to seconds
            "total_speakers": len(set(u["speaker"] for u in utterances))
        }