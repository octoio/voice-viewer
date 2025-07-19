"""
Base visualizer interface and utilities
"""

import numpy as np
import cv2
from abc import ABC, abstractmethod
from typing import Tuple, Optional

from ..audio import AudioFeatures
from ..config import Config


class BaseVisualizer(ABC):
    """Abstract base class for all visualizers"""
    
    def __init__(self, config: Config):
        self.config = config
        self.width, self.height = config.video.resolution
        self.theme = config.theme
        self.viz_config = config.visualizer
        
        # Convert hex colors to BGR for OpenCV
        self.bg_color = self._hex_to_bgr(self.theme.background)
        self.primary_color = self._hex_to_bgr(self.theme.primary)
        self.secondary_color = self._hex_to_bgr(self.theme.secondary)
        self.accent_color = self._hex_to_bgr(self.theme.accent)
    
    @abstractmethod
    def render_frame(self, features: AudioFeatures) -> np.ndarray:
        """Render a single frame based on audio features"""
        pass
    
    def _hex_to_bgr(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to BGR tuple for OpenCV"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (rgb[2], rgb[1], rgb[0])  # Convert RGB to BGR
    
    def _create_base_frame(self) -> np.ndarray:
        """Create a base frame with background color"""
        frame = np.full((self.height, self.width, 3), self.bg_color, dtype=np.uint8)
        return frame
    
    def _interpolate_color(self, color1: Tuple[int, int, int], 
                          color2: Tuple[int, int, int], 
                          factor: float) -> Tuple[int, int, int]:
        """Interpolate between two colors"""
        factor = np.clip(factor, 0.0, 1.0)
        return tuple(
            int(c1 + (c2 - c1) * factor) 
            for c1, c2 in zip(color1, color2)
        )
    
    def _apply_smoothing(self, current_values: np.ndarray, 
                        previous_values: Optional[np.ndarray]) -> np.ndarray:
        """Apply temporal smoothing to values with decay"""
        if previous_values is None:
            return current_values
        
        smoothing = self.viz_config.smoothing
        smoothed = smoothing * previous_values + (1 - smoothing) * current_values
        
        # Apply decay to prevent values from getting stuck
        decay_factor = 0.98  # Values decay by 2% per frame
        smoothed = smoothed * decay_factor
        
        # Apply floor clamping to ensure values can reach zero
        noise_floor = 0.01
        smoothed = np.where(smoothed < noise_floor, 0.0, smoothed)
        
        # Apply ceiling clamping to prevent runaway values
        smoothed = np.clip(smoothed, 0.0, 1.0)
        
        return smoothed
    
    def _normalize_spectrum(self, spectrum: np.ndarray) -> np.ndarray:
        """Normalize spectrum for visualization with robust clamping"""
        # Apply logarithmic scaling
        spectrum = np.log1p(spectrum * self.viz_config.sensitivity)
        
        # Use adaptive normalization with a moving maximum
        if not hasattr(self, '_max_spectrum_history'):
            self._max_spectrum_history = []
        
        current_max = spectrum.max() if spectrum.max() > 0 else 1.0
        self._max_spectrum_history.append(current_max)
        
        # Keep only recent history (last 30 frames for adaptive normalization)
        if len(self._max_spectrum_history) > 30:
            self._max_spectrum_history.pop(0)
        
        # Use 95th percentile of recent maxima to avoid spikes
        adaptive_max = np.percentile(self._max_spectrum_history, 95)
        
        # Normalize with adaptive maximum
        spectrum = spectrum / max(adaptive_max, 0.1)  # Prevent division by zero
        
        # Hard clamp to [0, 1] range
        spectrum = np.clip(spectrum, 0.0, 1.0)
        
        return spectrum
    
    def _downsample_spectrum(self, spectrum: np.ndarray, n_bars: int) -> np.ndarray:
        """Downsample spectrum to desired number of bars"""
        if len(spectrum) <= n_bars:
            return spectrum
        
        # Group frequencies into bins
        bin_size = len(spectrum) // n_bars
        downsampled = np.zeros(n_bars)
        
        for i in range(n_bars):
            start_idx = i * bin_size
            end_idx = min((i + 1) * bin_size, len(spectrum))
            downsampled[i] = np.mean(spectrum[start_idx:end_idx])
        
        return downsampled