"""
Whisper Inference Engine - Local HIPAA-Compliant Voice Transcription

Uses vLLM with Whisper model for on-premises speech-to-text.
Zero cloud - all audio processing happens on hospital hardware.
"""

import os
from typing import Optional
import tempfile
import subprocess

# vLLM support removed in favor of faster-whisper
VLLM_AVAILABLE = False


try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class WhisperTranscriber:
    """Local Whisper transcription engine"""

    def __init__(self, model_size: str = "base", device: str = "cuda"):
        """
        Initialize Whisper transcriber

        Args:
            model_size: "tiny", "base", "small", "medium", "large-v3"
                       - tiny: fastest, lowest accuracy (~1GB VRAM)
                       - base: good balance (~1GB VRAM) - RECOMMENDED for mobile
                       - small: better accuracy (~2GB VRAM)
                       - medium: high accuracy (~5GB VRAM)
                       - large-v3: best accuracy (~10GB VRAM)
            device: "cuda" or "cpu"
        """
        self.model_size = model_size
        self.device = device
        self.model = None

        # Initialize based on available backend
        if FASTER_WHISPER_AVAILABLE:
            print(f"🎤 Loading Whisper {model_size} with faster-whisper...")
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type="float16" if device == "cuda" else "int8"
            )
            self.backend = "faster-whisper"
        else:
            raise ImportError(
                "faster-whisper not available. "
                "Install with: pip install faster-whisper"
            )

    def transcribe_file(self, audio_path: str, language: str = "en") -> dict:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to audio file (wav, mp3, m4a, etc.)
            language: ISO language code ("en", "es", "zh", etc.)

        Returns:
            {
                "text": str,           # Full transcript
                "segments": List[dict], # Timestamped segments
                "language": str,       # Detected language
                "duration": float      # Audio duration in seconds
            }
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self.backend == "faster-whisper":
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            # Collect segments
            segment_list = []
            full_text = []

            for segment in segments:
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
                full_text.append(segment.text.strip())

            return {
                "text": " ".join(full_text),
                "segments": segment_list,
                "language": info.language,
                "duration": info.duration
            }



    def transcribe_bytes(self, audio_bytes: bytes, language: str = "en") -> dict:
        """
        Transcribe audio from bytes (for Streamlit audio input)

        Args:
            audio_bytes: Raw audio bytes
            language: ISO language code

        Returns:
            Same as transcribe_file()
        """
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = self.transcribe_file(tmp_path, language)
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# Global transcriber instance (lazy loaded)
_transcriber: Optional[WhisperTranscriber] = None


def get_transcriber(model_size: str = "base") -> WhisperTranscriber:
    """Get or create global transcriber instance"""
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber(model_size=model_size)
    return _transcriber


def whisper_transcribe(audio_path: str, language: str = "en") -> str:
    """
    Simple transcription function (for compatibility with existing code)

    Args:
        audio_path: Path to audio file
        language: Language code

    Returns:
        Transcript text
    """
    transcriber = get_transcriber()
    result = transcriber.transcribe_file(audio_path, language)
    return result["text"]


def transcribe_with_timestamps(audio_path: str, language: str = "en") -> dict:
    """
    Transcription with full metadata

    Returns complete dict with segments, timestamps, etc.
    """
    transcriber = get_transcriber()
    return transcriber.transcribe_file(audio_path, language)


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python whisper_inference.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]

    print(f"🎤 Transcribing: {audio_file}")
    result = transcribe_with_timestamps(audio_file)

    print(f"\n📝 Transcript ({result['duration']:.1f}s):")
    print(result['text'])

    if result['segments']:
        print(f"\n⏱️ Segments ({len(result['segments'])}):")
        for seg in result['segments'][:5]:  # Show first 5
            print(f"  [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
