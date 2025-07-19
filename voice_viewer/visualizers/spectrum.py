"""
Spectrum analyzer visualizer - frequency bars
"""

import numpy as np
import cv2
from typing import Optional

from .base import BaseVisualizer
from ..audio import AudioFeatures


class SpectrumVisualizer(BaseVisualizer):
    """Frequency spectrum visualizer with bars"""
    
    def __init__(self, config):
        super().__init__(config)
        self.previous_heights = None
        self.bar_width = self.width // self.viz_config.bars
        self.margin = self.width * 0.1  # 10% margin on each side
        self.bar_spacing = 2
        
        # Calculate actual bar width with spacing
        available_width = self.width - 2 * self.margin
        total_spacing = (self.viz_config.bars - 1) * self.bar_spacing
        self.bar_width = max(1, int((available_width - total_spacing) // self.viz_config.bars))
    
    def render_frame(self, features: AudioFeatures) -> np.ndarray:
        """Render spectrum bars frame"""
        frame = self._create_base_frame()
        
        # Normalize and downsample spectrum
        spectrum = self._normalize_spectrum(features.spectrum)
        spectrum = self._downsample_spectrum(spectrum, self.viz_config.bars)
        
        # Apply smoothing
        spectrum = self._apply_smoothing(spectrum, self.previous_heights)
        self.previous_heights = spectrum.copy()
        
        # Calculate bar dimensions
        max_bar_height = self.height * 0.8  # 80% of frame height
        base_y = int(self.height * 0.9)  # Start bars from bottom
        
        # Render bars
        for i, magnitude in enumerate(spectrum):
            bar_height = int(magnitude * max_bar_height)
            if bar_height < 1:
                continue
            
            # Calculate bar position
            x = int(self.margin + i * (self.bar_width + self.bar_spacing))
            y_top = base_y - bar_height
            y_bottom = base_y
            
            # Choose color based on frequency and magnitude
            color = self._get_bar_color(i, magnitude, len(spectrum))
            
            # Draw bar with gradient if enabled
            if self.theme.gradient:
                self._draw_gradient_bar(frame, x, y_top, y_bottom, color)
            else:
                cv2.rectangle(frame, (x, y_top), (x + self.bar_width, y_bottom), color, -1)
            
            # Add glow effect for high amplitudes
            if magnitude > 0.7:
                self._add_glow_effect(frame, x, y_top, y_bottom, color)
        
        return frame
    
    def _get_bar_color(self, bar_index: int, magnitude: float, total_bars: int):
        """Get color for bar based on frequency and magnitude"""
        # Create color gradient from low to high frequencies
        freq_ratio = bar_index / max(1, total_bars - 1)
        
        if freq_ratio < 0.33:  # Low frequencies - primary color
            base_color = self.primary_color
        elif freq_ratio < 0.66:  # Mid frequencies - secondary color
            base_color = self.secondary_color
        else:  # High frequencies - accent color
            base_color = self.accent_color
        
        # Modulate brightness based on magnitude
        brightness = 0.3 + 0.7 * magnitude  # Min 30%, max 100% brightness
        return tuple(int(c * brightness) for c in base_color)
    
    def _draw_gradient_bar(self, frame: np.ndarray, x: int, y_top: int, y_bottom: int, color: tuple):
        """Draw a gradient-filled bar"""
        bar_height = y_bottom - y_top
        if bar_height <= 0:
            return
        
        # Create gradient from dark to full color
        dark_color = tuple(int(c * 0.2) for c in color)
        
        for y in range(y_top, y_bottom):
            # Calculate gradient factor (bottom is full color, top is dark)
            gradient_factor = (y_bottom - y) / bar_height
            current_color = self._interpolate_color(color, dark_color, gradient_factor)
            
            cv2.rectangle(frame, (x, y), (x + self.bar_width, y + 1), current_color, -1)
    
    def _add_glow_effect(self, frame: np.ndarray, x: int, y_top: int, y_bottom: int, color: tuple):
        """Add glow effect around high-magnitude bars"""
        glow_radius = 3
        glow_color = tuple(int(c * 0.5) for c in color)
        
        # Draw glow as semi-transparent rectangles
        for radius in range(1, glow_radius + 1):
            alpha = 0.3 / radius  # Fade out with distance
            glow_x1 = max(0, x - radius)
            glow_y1 = max(0, y_top - radius)
            glow_x2 = min(self.width, x + self.bar_width + radius)
            glow_y2 = min(self.height, y_bottom + radius)
            
            # Create overlay for alpha blending
            overlay = frame.copy()
            cv2.rectangle(overlay, (glow_x1, glow_y1), (glow_x2, glow_y2), glow_color, -1)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)