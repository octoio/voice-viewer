"""
Configuration models and settings for voice viewer
"""

from typing import Tuple, Optional
from pydantic import BaseModel, Field


class VideoConfig(BaseModel):
    """Video output configuration"""
    resolution: Tuple[int, int] = Field(default=(1920, 1080), description="Video resolution (width, height)")
    fps: int = Field(default=30, ge=1, le=120, description="Frames per second")
    bitrate: str = Field(default="5M", description="Video bitrate")
    codec: str = Field(default="libx264", description="Video codec")


class AudioConfig(BaseModel):
    """Audio processing configuration"""
    sample_rate: int = Field(default=44100, description="Audio sample rate")
    buffer_size: int = Field(default=1024, description="Buffer size for analysis")
    hop_length: int = Field(default=512, description="Hop length for FFT")
    noise_reduction: bool = Field(default=True, description="Enable noise reduction")


class VisualizerConfig(BaseModel):
    """Visualizer-specific configuration"""
    type: str = Field(default="spectrum", description="Visualizer type")
    smoothing: float = Field(default=0.8, ge=0.0, le=1.0, description="Smoothing factor")
    sensitivity: float = Field(default=1.2, ge=0.1, le=5.0, description="Audio sensitivity")
    bars: int = Field(default=64, ge=8, le=256, description="Number of frequency bars")
    rotation_speed: float = Field(default=0.0, ge=-5.0, le=5.0, description="Outer circle rotation speed (degrees per frame, 0=no rotation)")
    inner_rotation_speed: float = Field(default=0.0, ge=-5.0, le=5.0, description="Inner circle rotation speed (degrees per frame, 0=no rotation)")
    min_radius: float = Field(default=0.15, ge=0.0, le=1.0, description="Minimum outer circle radius (0=no circle, 1=full screen)")
    max_radius: float = Field(default=0.35, ge=0.0, le=1.0, description="Maximum outer circle radius (0=no circle, 1=full screen)")
    inner_min_radius: float = Field(default=0.05, ge=0.0, le=1.0, description="Minimum inner circle radius (0=no circle, 1=full screen)")
    inner_max_radius: float = Field(default=0.2, ge=0.0, le=1.0, description="Maximum inner circle radius (0=no circle, 1=full screen)")
    inner_bars: int = Field(default=32, ge=4, le=128, description="Number of frequency bars for inner circle")


class ThemeConfig(BaseModel):
    """Visual theme configuration"""
    background: str = Field(default="#1a1a1a", description="Background color")
    primary: str = Field(default="#00ff88", description="Primary color")
    secondary: str = Field(default="#ffffff", description="Secondary color")
    accent: str = Field(default="#ff6b6b", description="Accent color")
    gradient: bool = Field(default=True, description="Use gradient effects")


class Config(BaseModel):
    """Main configuration model"""
    video: VideoConfig = Field(default_factory=VideoConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    visualizer: VisualizerConfig = Field(default_factory=VisualizerConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    
    @classmethod
    def load_theme(cls, theme_name: str) -> "Config":
        """Load a predefined theme"""
        themes = {
            "professional": cls._professional_theme(),
            "dark": cls._dark_theme(),
            "colorful": cls._colorful_theme(),
            "minimal": cls._minimal_theme()
        }
        return themes.get(theme_name, cls())
    
    @classmethod
    def _professional_theme(cls) -> "Config":
        """Professional theme for technical content"""
        config = cls()
        config.theme.background = "#1a1a1a"
        config.theme.primary = "#00ff88"
        config.theme.secondary = "#ffffff"
        config.theme.accent = "#64ffda"
        config.visualizer.smoothing = 0.9
        config.visualizer.sensitivity = 1.0
        return config
    
    @classmethod
    def _dark_theme(cls) -> "Config":
        """Dark theme"""
        config = cls()
        config.theme.background = "#0d1117"
        config.theme.primary = "#58a6ff"
        config.theme.secondary = "#f0f6fc"
        config.theme.accent = "#ffa657"
        return config
    
    @classmethod
    def _colorful_theme(cls) -> "Config":
        """Colorful theme"""
        config = cls()
        config.theme.background = "#000000"
        config.theme.primary = "#ff0080"
        config.theme.secondary = "#00ff80"
        config.theme.accent = "#8000ff"
        config.visualizer.sensitivity = 1.5
        return config
    
    @classmethod
    def _minimal_theme(cls) -> "Config":
        """Minimal theme - simple white on black"""
        config = cls()
        config.theme.background = "#000000"
        config.theme.primary = "#ffffff"
        config.theme.secondary = "#cccccc"
        config.theme.accent = "#ffffff"
        config.theme.gradient = False
        config.visualizer.type = "circular"
        config.visualizer.smoothing = 0.6  # Reduced from 0.9 for faster response
        config.visualizer.sensitivity = 1.0
        config.visualizer.bars = 48
        return config