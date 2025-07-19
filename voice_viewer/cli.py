"""
Command-line interface for voice viewer
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
from .export import VideoRenderer
from .visualizers import VISUALIZERS

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """Voice Viewer - Professional Audio Visualizer"""
    pass


@main.command()
@click.argument('audio_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output video file path')
@click.option('--visualizer', '-v', type=click.Choice(list(VISUALIZERS.keys())), 
              default='spectrum', help='Visualizer type')
@click.option('--theme', '-t', type=click.Choice(['professional', 'dark', 'colorful', 'minimal']), 
              default='professional', help='Visual theme')
@click.option('--resolution', '-r', type=click.Choice(['720p', '1080p', '4k']), 
              default='1080p', help='Video resolution')
@click.option('--fps', type=click.IntRange(15, 120), default=30, 
              help='Frames per second')
@click.option('--bars', type=click.IntRange(8, 256), default=64,
              help='Number of frequency bars (spectrum visualizer)')
@click.option('--rotation', type=click.FloatRange(-5.0, 5.0), default=0.0,
              help='Outer circle rotation speed in degrees per frame (circular visualizer only)')
@click.option('--inner-rotation', type=click.FloatRange(-5.0, 5.0), default=0.0,
              help='Inner circle rotation speed in degrees per frame (circular visualizer only)')
@click.option('--min-radius', type=click.FloatRange(0.0, 1.0), default=0.15,
              help='Minimum outer circle radius (0=no circle, 1=full screen)')
@click.option('--max-radius', type=click.FloatRange(0.0, 1.0), default=0.35,
              help='Maximum outer circle radius (0=no circle, 1=full screen)')
@click.option('--inner-min-radius', type=click.FloatRange(0.0, 1.0), default=0.05,
              help='Minimum inner circle radius (0=no circle, 1=full screen)')
@click.option('--inner-max-radius', type=click.FloatRange(0.0, 1.0), default=0.2,
              help='Maximum inner circle radius (0=no circle, 1=full screen)')
@click.option('--inner-bars', type=click.IntRange(4, 128), default=32,
              help='Number of frequency bars for inner circle (circular visualizer only)')
@click.option('--config', type=click.Path(exists=True, path_type=Path),
              help='Load configuration JSON file (overrides other parameters)')
def generate(audio_file, output, visualizer, theme, resolution, fps, bars, rotation, inner_rotation, min_radius, max_radius, inner_min_radius, inner_max_radius, inner_bars, config):
    """Generate video visualization from audio file
    
    Examples:
        # Basic usage
        python -m voice_viewer generate audio.wav
        
        # Use config file (from live mode or custom)
        python -m voice_viewer generate audio.wav --config settings.json
        
        # Manual parameters (ignored if --config is used)
        python -m voice_viewer generate audio.wav --rotation 2.0 --inner-rotation -1.5
    """
    
    # Set default output path if not provided
    if output is None:
        output = audio_file.with_suffix('.mp4')
    
    # Create config
    if config:
        # Load config from live session
        import json
        with open(config, 'r') as f:
            saved_config = json.load(f)
        config_obj = Config.load_theme(saved_config.get('theme', theme))
        
        # Apply saved visualizer settings
        for key, value in saved_config.get('visualizer', {}).items():
            setattr(config_obj.visualizer, key, value)
        
        console.print(f"📁 Loaded config from: [cyan]{config}[/cyan]")
    else:
        # Use command line parameters
        config_obj = Config.load_theme(theme)
        config_obj.visualizer.type = visualizer
        config_obj.visualizer.bars = bars
        config_obj.visualizer.rotation_speed = rotation
        config_obj.visualizer.inner_rotation_speed = inner_rotation
        config_obj.visualizer.min_radius = min_radius
        config_obj.visualizer.max_radius = max_radius
        config_obj.visualizer.inner_min_radius = inner_min_radius
        config_obj.visualizer.inner_max_radius = inner_max_radius
        config_obj.visualizer.inner_bars = inner_bars
    
    config_obj.video.fps = fps
    
    # Set resolution
    resolutions = {
        '720p': (1280, 720),
        '1080p': (1920, 1080),
        '4k': (3840, 2160)
    }
    config_obj.video.resolution = resolutions[resolution]
    
    console.print(f"🎵 Processing: [cyan]{audio_file}[/cyan]")
    console.print(f"🎨 Visualizer: [green]{visualizer}[/green] | Theme: [blue]{theme}[/blue]")
    console.print(f"📺 Resolution: [yellow]{resolution}[/yellow] | FPS: [magenta]{fps}[/magenta]")
    
    # Render video
    renderer = VideoRenderer(config_obj)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Rendering video...", total=None)
        
        success = renderer.render_video(str(audio_file), str(output))
        
        if success:
            progress.update(task, description="✅ Rendering complete!")
            console.print(f"🎬 Output saved: [green]{output}[/green]")
        else:
            progress.update(task, description="❌ Rendering failed!")
            console.print("[red]Error: Failed to generate video[/red]")


@main.command()
@click.argument('audio_file', type=click.Path(exists=True, path_type=Path))
@click.option('--visualizer', '-v', type=click.Choice(list(VISUALIZERS.keys())), 
              default='spectrum', help='Visualizer type')
@click.option('--theme', '-t', type=click.Choice(['professional', 'dark', 'colorful', 'minimal']), 
              default='professional', help='Visual theme')
def preview(audio_file, visualizer, theme):
    """Preview visualization in real-time"""
    
    config = Config.load_theme(theme)
    config.visualizer.type = visualizer
    
    console.print(f"🎵 Previewing: [cyan]{audio_file}[/cyan]")
    console.print(f"🎨 Visualizer: [green]{visualizer}[/green] | Theme: [blue]{theme}[/blue]")
    console.print("💡 Press [yellow]SPACE[/yellow] to pause/resume, [red]Q[/red] to quit")
    
    renderer = VideoRenderer(config)
    renderer.render_video(str(audio_file), "", preview=True)


@main.command()
@click.option('--theme', '-t', type=click.Choice(['professional', 'dark', 'colorful', 'minimal']), 
              default='minimal', help='Visual theme')
@click.option('--save-config', type=click.Path(path_type=Path), 
              help='Save final configuration to file for later use')
def live(theme, save_config):
    """Live microphone visualization with GUI parameter controls"""
    
    from .live import LiveVisualizerGUI
    
    console.print("🎤 [bold green]Live Microphone Mode - GUI[/bold green]")
    console.print(f"🎨 Theme: [blue]{theme}[/blue]")
    console.print("🖱️  Use GUI sliders to adjust parameters in real-time")
    console.print("💡 Close window to quit and save config")
    console.print("📺 Running at 640x480 for fast performance")
    
    live_viz = LiveVisualizerGUI(theme, save_config)
    live_viz.run()


@main.command()
def themes():
    """List available themes"""
    console.print("🎨 Available Themes:")
    console.print("  • [green]professional[/green] - Clean, technical aesthetic")
    console.print("  • [blue]dark[/blue] - Dark mode with blue accents")
    console.print("  • [magenta]colorful[/magenta] - Vibrant, dynamic colors")
    console.print("  • [white]minimal[/white] - Simple white on black circular")


@main.command()
def visualizers():
    """List available visualizers"""
    console.print("🎵 Available Visualizers:")
    for name, cls in VISUALIZERS.items():
        doc = cls.__doc__ or "No description"
        console.print(f"  • [cyan]{name}[/cyan] - {doc}")


if __name__ == "__main__":
    main()
