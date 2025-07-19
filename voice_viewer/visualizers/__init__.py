"""
Visualizers module
"""

from .base import BaseVisualizer
from .spectrum import SpectrumVisualizer
from .waveform import WaveformVisualizer
from .circular import CircularVisualizer

# Visualizer registry
VISUALIZERS = {
    "spectrum": SpectrumVisualizer,
    "waveform": WaveformVisualizer,
    "circular": CircularVisualizer,
}

def get_visualizer(name: str, config):
    """Get visualizer by name"""
    if name not in VISUALIZERS:
        available = ", ".join(VISUALIZERS.keys())
        raise ValueError(f"Unknown visualizer '{name}'. Available: {available}")
    
    return VISUALIZERS[name](config)

__all__ = ["BaseVisualizer", "SpectrumVisualizer", "WaveformVisualizer", "CircularVisualizer", "get_visualizer", "VISUALIZERS"]