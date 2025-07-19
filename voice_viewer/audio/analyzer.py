"""
Real-time audio analysis and feature extraction
"""

import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional, Iterator
from dataclasses import dataclass

from ..config import AudioConfig


@dataclass
class AudioFeatures:
    """Container for extracted audio features"""
    timestamp: float
    amplitude: float
    spectrum: np.ndarray
    frequencies: np.ndarray
    onset: bool = False
    rms: float = 0.0
    centroid: float = 0.0


class AudioAnalyzer:
    """Real-time audio analysis engine"""
    
    def __init__(self, config: AudioConfig):
        self.config = config
        self.sample_rate = config.sample_rate
        self.buffer_size = config.buffer_size
        self.hop_length = config.hop_length
        
        # Pre-compute frequency bins
        self.frequencies = librosa.fft_frequencies(
            sr=self.sample_rate, 
            n_fft=self.buffer_size
        )
        
        # Smoothing buffer for spectrum
        self.prev_spectrum = None
        
    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, float]:
        """Load audio file and return samples with duration"""
        try:
            audio, sr = librosa.load(
                audio_path, 
                sr=self.sample_rate,
                mono=True
            )
            duration = len(audio) / sr
            return audio, duration
        except Exception as e:
            raise ValueError(f"Failed to load audio file: {e}")
    
    def analyze_frame(self, audio_frame: np.ndarray, timestamp: float) -> AudioFeatures:
        """Analyze a single audio frame and extract features"""
        # Ensure frame has correct length
        if len(audio_frame) < self.buffer_size:
            # Pad with zeros if frame is too short
            padded = np.zeros(self.buffer_size)
            padded[:len(audio_frame)] = audio_frame
            audio_frame = padded
        elif len(audio_frame) > self.buffer_size:
            # Truncate if frame is too long
            audio_frame = audio_frame[:self.buffer_size]
        
        # Apply noise reduction if enabled
        if self.config.noise_reduction:
            audio_frame = self._reduce_noise(audio_frame)
        
        # Compute amplitude (RMS)
        rms = np.sqrt(np.mean(audio_frame**2))
        amplitude = rms
        
        # Compute frequency spectrum using STFT
        stft = librosa.stft(
            audio_frame,
            n_fft=self.buffer_size,
            hop_length=self.hop_length
        )
        spectrum = np.abs(stft).mean(axis=1)  # Average across time
        
        # Apply smoothing (less aggressive for faster response)
        if self.prev_spectrum is not None:
            spectrum = 0.5 * spectrum + 0.5 * self.prev_spectrum  # More responsive
        self.prev_spectrum = spectrum.copy()
        
        # Compute spectral centroid
        try:
            centroid = librosa.feature.spectral_centroid(
                y=audio_frame,
                sr=self.sample_rate
            )[0].mean()
        except (AttributeError, IndexError):
            # Fallback if spectral_centroid fails
            centroid = 0.0
        
        # Simple onset detection (energy-based)
        onset = self._detect_onset(audio_frame)
        
        return AudioFeatures(
            timestamp=timestamp,
            amplitude=amplitude,
            spectrum=spectrum,
            frequencies=self.frequencies,
            onset=onset,
            rms=rms,
            centroid=centroid
        )
    
    def process_audio_stream(self, audio: np.ndarray, fps: int) -> Iterator[AudioFeatures]:
        """Process audio in chunks matching video framerate"""
        samples_per_frame = self.sample_rate // fps
        total_frames = len(audio) // samples_per_frame
        
        for i in range(total_frames):
            start_idx = i * samples_per_frame
            end_idx = start_idx + self.buffer_size
            
            # Handle edge case at end of audio
            if end_idx > len(audio):
                frame = np.zeros(self.buffer_size)
                remaining = len(audio) - start_idx
                if remaining > 0:
                    frame[:remaining] = audio[start_idx:]
            else:
                frame = audio[start_idx:end_idx]
            
            timestamp = i / fps
            yield self.analyze_frame(frame, timestamp)
    
    def _reduce_noise(self, audio_frame: np.ndarray) -> np.ndarray:
        """Simple noise reduction using spectral gating"""
        # Compute noise floor (bottom 10% of spectrum energy)
        spectrum = np.abs(np.fft.fft(audio_frame))
        noise_floor = np.percentile(spectrum, 10)
        
        # Apply spectral gate
        threshold = noise_floor * 2.0
        mask = spectrum > threshold
        
        # Apply mask in frequency domain
        fft_frame = np.fft.fft(audio_frame)
        fft_frame[~mask] *= 0.1  # Reduce noise components
        
        return np.real(np.fft.ifft(fft_frame))
    
    def _detect_onset(self, audio_frame: np.ndarray) -> bool:
        """Simple energy-based onset detection"""
        if not hasattr(self, '_prev_energy'):
            self._prev_energy = 0.0
        
        current_energy = np.sum(audio_frame**2)
        onset = current_energy > self._prev_energy * 1.5
        self._prev_energy = current_energy
        
        return onset