"""
Waveform visualizer - classic audio waveform display
"""

import numpy as np
import cv2
from typing import Optional, List

from .base import BaseVisualizer
from ..audio import AudioFeatures


class WaveformVisualizer(BaseVisualizer):
    """Classic waveform visualizer"""
    
    def __init__(self, config):
        super().__init__(config)
        self.waveform_history: List[float] = []
        self.history_length = self.width // 4  # Show 1/4 second of history
        self.center_y = self.height // 2
        self.max_amplitude = self.height * 0.4  # Max waveform height
    
    def render_frame(self, features: AudioFeatures) -> np.ndarray:
        """Render waveform frame"""
        frame = self._create_base_frame()
        
        # Add current amplitude to history
        self.waveform_history.append(features.amplitude)
        
        # Maintain history length
        if len(self.waveform_history) > self.history_length:
            self.waveform_history.pop(0)
        
        # Draw center line
        cv2.line(frame, (0, self.center_y), (self.width, self.center_y), 
                self.secondary_color, 1, cv2.LINE_AA)
        
        # Draw waveform
        if len(self.waveform_history) > 1:
            self._draw_waveform(frame)
        
        # Draw current amplitude indicator
        self._draw_amplitude_indicator(frame, features.amplitude)
        
        # Add frequency analysis overlay
        if features.spectrum is not None:
            self._draw_frequency_overlay(frame, features)
        
        return frame
    
    def _draw_waveform(self, frame: np.ndarray):
        """Draw the waveform line"""
        points = []
        x_step = self.width / max(1, len(self.waveform_history) - 1)
        
        for i, amplitude in enumerate(self.waveform_history):
            x = int(i * x_step)
            
            # Scale amplitude to pixels
            amplitude_scaled = amplitude * self.viz_config.sensitivity
            y_offset = int(amplitude_scaled * self.max_amplitude)
            
            # Add both positive and negative points for stereo effect
            y_pos = self.center_y - y_offset
            y_neg = self.center_y + y_offset
            
            points.append((x, y_pos))
        
        # Draw waveform line with anti-aliasing
        if len(points) > 1:
            # Convert to numpy array for OpenCV
            pts = np.array(points, dtype=np.int32)
            
            # Draw main waveform
            for i in range(len(pts) - 1):
                cv2.line(frame, tuple(pts[i]), tuple(pts[i + 1]), 
                        self.primary_color, 2, cv2.LINE_AA)
            
            # Draw mirrored waveform below center
            pts_mirror = pts.copy()
            pts_mirror[:, 1] = 2 * self.center_y - pts_mirror[:, 1]
            
            for i in range(len(pts_mirror) - 1):
                cv2.line(frame, tuple(pts_mirror[i]), tuple(pts_mirror[i + 1]), 
                        self.primary_color, 2, cv2.LINE_AA)
    
    def _draw_amplitude_indicator(self, frame: np.ndarray, amplitude: float):
        """Draw current amplitude level indicator"""
        # Right side amplitude meter
        meter_x = self.width - 30
        meter_top = int(self.height * 0.1)
        meter_bottom = int(self.height * 0.9)
        meter_height = meter_bottom - meter_top
        
        # Background meter
        cv2.rectangle(frame, (meter_x, meter_top), (meter_x + 20, meter_bottom), 
                     self.secondary_color, 1)
        
        # Current level
        level_height = int(amplitude * self.viz_config.sensitivity * meter_height)
        level_top = meter_bottom - level_height
        
        if level_height > 0:
            # Color based on amplitude level
            if amplitude > 0.8:
                color = (0, 0, 255)  # Red for high levels
            elif amplitude > 0.5:
                color = (0, 165, 255)  # Orange for medium levels
            else:
                color = self.primary_color  # Primary color for normal levels
            
            cv2.rectangle(frame, (meter_x + 2, level_top), (meter_x + 18, meter_bottom), 
                         color, -1)
    
    def _draw_frequency_overlay(self, frame: np.ndarray, features: AudioFeatures):
        """Draw subtle frequency analysis overlay"""
        if features.spectrum is None or len(features.spectrum) == 0:
            return
        
        # Get dominant frequency
        spectrum = self._normalize_spectrum(features.spectrum)
        dominant_freq_idx = np.argmax(spectrum)
        dominant_magnitude = spectrum[dominant_freq_idx]
        
        if dominant_magnitude > 0.3:  # Only show if significant
            # Map frequency to color
            freq_ratio = dominant_freq_idx / len(spectrum)
            
            if freq_ratio < 0.33:
                freq_color = self.accent_color
            elif freq_ratio < 0.66:
                freq_color = self.primary_color
            else:
                freq_color = self.secondary_color
            
            # Draw subtle frequency indicator circles
            circle_radius = int(dominant_magnitude * 20)
            circle_alpha = dominant_magnitude * 0.5
            
            # Create overlay for transparency
            overlay = frame.copy()
            cv2.circle(overlay, (self.width // 4, self.center_y), 
                      circle_radius, freq_color, -1)
            cv2.circle(overlay, (3 * self.width // 4, self.center_y), 
                      circle_radius, freq_color, -1)
            
            # Blend with main frame
            cv2.addWeighted(overlay, circle_alpha, frame, 1 - circle_alpha, 0, frame)