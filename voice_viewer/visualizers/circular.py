"""
Circular visualizer - deforming circle based on audio spectrum
"""

import numpy as np
import cv2
import math
from typing import Optional

from .base import BaseVisualizer
from ..audio import AudioFeatures


class CircularVisualizer(BaseVisualizer):
    """Deforming circle visualizer - circle radius changes with frequency"""
    
    def __init__(self, config):
        super().__init__(config)
        self.previous_spectrum = None
        
        # Circular parameters
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        # Normalized radius calculations (0.5 = half screen height)
        screen_half_height = self.height // 2
        self.min_radius = screen_half_height * self.viz_config.min_radius
        self.max_radius = screen_half_height * self.viz_config.max_radius
        self.radius_range = self.max_radius - self.min_radius
        
        # Inner circle parameters (same normalization)
        self.inner_min_radius = screen_half_height * self.viz_config.inner_min_radius
        self.inner_max_radius = screen_half_height * self.viz_config.inner_max_radius
        self.inner_radius_range = self.inner_max_radius - self.inner_min_radius
        
        # Circle segments based on bars setting
        self.circle_segments = self.viz_config.bars * 2  # 2x bars for smooth circle
        self.angle_step = 2 * math.pi / self.circle_segments
        
        # Inner circle segments
        self.inner_circle_segments = self.viz_config.inner_bars * 2
        self.inner_angle_step = 2 * math.pi / self.inner_circle_segments
        
        # Rotation tracking
        self.current_rotation = 0.0  # Current outer circle rotation in radians
        self.current_inner_rotation = 0.0  # Current inner circle rotation in radians
        
        # Frequency mapping - distribute mid frequencies around circle
        self.freq_mapping = self._create_frequency_mapping(self.circle_segments, self.viz_config.bars)
        self.inner_freq_mapping = self._create_frequency_mapping(self.inner_circle_segments, self.viz_config.inner_bars)  # Different random distribution for inner circle
        
        # Track frequency activity for adaptive amplification
        self.freq_activity = np.ones(self.viz_config.bars)
        self.inner_freq_activity = np.ones(self.viz_config.inner_bars)
    
    def render_frame(self, features: AudioFeatures) -> np.ndarray:
        """Render deforming circle frame"""
        frame = self._create_base_frame()
        
        # Update rotations for both circles
        rotation_speed_radians = math.radians(self.viz_config.rotation_speed)
        self.current_rotation += rotation_speed_radians
        
        inner_rotation_speed_radians = math.radians(self.viz_config.inner_rotation_speed)
        self.current_inner_rotation += inner_rotation_speed_radians
        
        # Normalize and process spectrum
        spectrum = self._normalize_spectrum(features.spectrum)
        
        # Apply smoothing
        spectrum = self._apply_smoothing(spectrum, self.previous_spectrum)
        self.previous_spectrum = spectrum.copy()
        
        # Apply adaptive amplification to boost inactive frequencies
        spectrum = self._apply_adaptive_amplification(spectrum)
        inner_spectrum = self._apply_adaptive_amplification(spectrum, inner=True)
        
        # Create deformed circle points for both circles
        outer_circle_points = self._create_deformed_circle(spectrum, self.freq_mapping)
        inner_circle_points = self._create_deformed_circle(inner_spectrum, self.inner_freq_mapping, inner=True)
        
        # Draw the outer white circle
        self._draw_deformed_circle(frame, outer_circle_points, self.primary_color)
        
        # Draw the inner black circle on top
        self._draw_deformed_circle(frame, inner_circle_points, self.bg_color)
        
        return frame
    
    def _create_frequency_mapping(self, circle_segments: int, bars: int):
        """Create randomized mapping to distribute frequencies around circle"""
        # Create array of frequency indices
        freq_indices = np.arange(bars)
        
        # Repeat to fill all circle segments
        repeats = (circle_segments // bars) + 1
        freq_indices = np.tile(freq_indices, repeats)[:circle_segments]
        
        # Randomize the order to spread frequencies around circle
        np.random.shuffle(freq_indices)
        
        return freq_indices
    
    def _apply_adaptive_amplification(self, spectrum: np.ndarray, inner: bool = False) -> np.ndarray:
        """Amplify frequencies that are consistently low to increase visual feedback"""
        # Downsample spectrum to match frequency tracking
        bars = self.viz_config.inner_bars if inner else self.viz_config.bars
        spectrum_small = self._downsample_spectrum(spectrum, bars)
        
        # Update activity tracking (exponential moving average)
        decay = 0.95
        freq_activity = self.inner_freq_activity if inner else self.freq_activity
        freq_activity[:] = decay * freq_activity + (1 - decay) * spectrum_small
        
        # Calculate amplification factors (inverse of activity)
        # Low activity frequencies get higher amplification
        min_activity = 0.1  # Prevent division by very small numbers
        max_amplification = 3.0  # Cap amplification to avoid overboost
        
        amplification = np.clip(
            min_activity / np.maximum(freq_activity, min_activity * 0.1),
            1.0,  # Minimum amplification (no reduction)
            max_amplification
        )
        
        # Apply amplification back to full spectrum
        amplified_spectrum = spectrum.copy()
        if len(spectrum) > bars:
            # Upsample amplification factors to match full spectrum
            bin_size = len(spectrum) // bars
            for i in range(bars):
                start_idx = i * bin_size
                end_idx = min((i + 1) * bin_size, len(spectrum))
                amplified_spectrum[start_idx:end_idx] *= amplification[i]
        else:
            amplified_spectrum *= amplification[:len(spectrum)]
        
        return amplified_spectrum
    
    def _create_deformed_circle(self, spectrum: np.ndarray, freq_mapping: np.ndarray, inner: bool = False) -> np.ndarray:
        """Create circle points deformed by spectrum"""
        # Use appropriate parameters for inner vs outer circle
        if inner:
            bars = self.viz_config.inner_bars
            circle_segments = self.inner_circle_segments
            angle_step = self.inner_angle_step
            min_radius = self.inner_min_radius
            radius_range = self.inner_radius_range
        else:
            bars = self.viz_config.bars
            circle_segments = self.circle_segments
            angle_step = self.angle_step
            min_radius = self.min_radius
            radius_range = self.radius_range
        
        # Downsample spectrum to match our frequency mapping
        spectrum_small = self._downsample_spectrum(spectrum, bars)
        
        points = []
        for i in range(circle_segments):
            # Apply rotation to the angle (use appropriate rotation for inner vs outer circle)
            rotation = self.current_inner_rotation if inner else self.current_rotation
            angle = i * angle_step + rotation
            
            # Get frequency index for this angle position
            freq_idx = freq_mapping[i] if i < len(freq_mapping) else i % len(spectrum_small)
            if freq_idx < len(spectrum_small):
                magnitude = spectrum_small[freq_idx]
            else:
                magnitude = 0.0
            
            # Calculate radius based on magnitude
            radius = min_radius + magnitude * radius_range * self.viz_config.sensitivity
            
            # Calculate point position
            x = self.center_x + radius * math.cos(angle)
            y = self.center_y + radius * math.sin(angle)
            
            points.append([int(x), int(y)])
        
        return np.array(points, dtype=np.int32)
    
    def _draw_deformed_circle(self, frame: np.ndarray, points: np.ndarray, color: tuple):
        """Draw the deformed circle using connected points"""
        if len(points) < 3:
            return
        
        # Draw filled polygon (deformed circle)
        cv2.fillPoly(frame, [points], color, cv2.LINE_AA)
        
        # Draw outline for definition (same color as fill)
        cv2.polylines(frame, [points], True, color, 2, cv2.LINE_AA)