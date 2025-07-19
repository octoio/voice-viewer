"""
Simple GUI live visualization with parameter controls
"""

import cv2
import numpy as np
import threading
import time
import json
from typing import Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

from .config import Config
from .audio import AudioAnalyzer
from .visualizers import VISUALIZERS


class LiveVisualizerGUI:
    """Simple GUI for live microphone visualization"""
    
    def __init__(self, theme: str, save_config_path: Optional[str] = None):
        self.theme = theme
        self.save_config_path = save_config_path
        
        # Config - adjust audio settings for live mode
        self.config = Config.load_theme(theme)
        self.config.visualizer.type = "circular"
        self.config.video.resolution = (640, 480)
        # Use smaller buffer and n_fft for live mode to avoid librosa warnings
        self.config.audio.buffer_size = 2048  # Increase buffer size
        self.config.audio.hop_length = 512    # Keep hop length smaller than buffer
        
        # Audio
        self.analyzer = AudioAnalyzer(self.config.audio)
        self.audio_buffer = np.zeros(self.analyzer.buffer_size, dtype=np.float32)
        self.mic_stream = None
        self.audio_interface = None
        
        # Visualization
        self.visualizer = None
        self.current_frame = None
        self.is_playing = False
        
        # Threading
        self.stop_flag = threading.Event()
        self.audio_thread = None
        self.display_thread = None
        
        # GUI
        self.root = None
        self.create_gui()
    
    def create_gui(self):
        """Create the GUI interface"""
        self.root = tk.Tk()
        self.root.title("Voice Viewer - Live Mode")
        self.root.geometry("450x600")
        self.root.resizable(False, False)
        
        # Force window update and visibility
        self.root.update_idletasks()
        self.root.update()
        
        # macOS specific fixes
        try:
            # Bring window to front
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after_idle(lambda: self.root.attributes('-topmost', False))
            
            # Set focus
            self.root.focus_force()
            
            # macOS specific commands
            self.root.createcommand('::tk::mac::ReopenApplication', self.root.deiconify)
            
            # Force refresh on macOS
            self.root.after(100, lambda: self.root.deiconify())
        except Exception:
            pass
        
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=10, pady=5)
        
        header_label = ttk.Label(header_frame, text="🎵 Voice Viewer - Live Mode", 
                 font=("Arial", 14, "bold"))
        header_label.pack()
        
        info_label = ttk.Label(header_frame, text=f"Theme: {self.theme} | Resolution: 640x480")
        info_label.pack()
        
        print(f"Created header frame: {header_frame}")
        print(f"Created header label: {header_label}")
        print(f"Created info label: {info_label}")
        
        # Control buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        self.play_button = ttk.Button(control_frame, text="▶ Start", command=self.toggle_playback)
        self.play_button.pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="Load Config", command=self.load_config_dialog).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Save Config", command=self.save_config_dialog).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Reset", command=self.reset_params).pack(side="left", padx=5)
        
        # Parameters frame
        params_frame = ttk.LabelFrame(self.root, text="Parameters", padding=10)
        params_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create parameter controls
        self.param_vars = {}
        self.create_parameter_controls(params_frame)
        
        # Status
        self.status_var = tk.StringVar(value="Ready - Press Start to begin")
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack()
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_parameter_controls(self, parent):
        """Create controls for all parameters"""
        row = 0
        
        # Sensitivity
        ttk.Label(parent, text="Sensitivity:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["sensitivity"] = tk.DoubleVar(value=self.config.visualizer.sensitivity)
        sensitivity_scale = ttk.Scale(parent, from_=0.1, to=3.0, orient="horizontal",
                                    variable=self.param_vars["sensitivity"], command=self.update_sensitivity)
        sensitivity_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.sensitivity_label = ttk.Label(parent, text=f"{self.config.visualizer.sensitivity:.2f}")
        self.sensitivity_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Outer Rotation Speed
        ttk.Label(parent, text="Outer Rotation:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["rotation_speed"] = tk.DoubleVar(value=self.config.visualizer.rotation_speed)
        rotation_scale = ttk.Scale(parent, from_=-5.0, to=5.0, orient="horizontal",
                                 variable=self.param_vars["rotation_speed"], command=self.update_rotation)
        rotation_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.rotation_label = ttk.Label(parent, text=f"{self.config.visualizer.rotation_speed:.2f}")
        self.rotation_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Inner Rotation Speed
        ttk.Label(parent, text="Inner Rotation:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["inner_rotation_speed"] = tk.DoubleVar(value=self.config.visualizer.inner_rotation_speed)
        inner_rotation_scale = ttk.Scale(parent, from_=-5.0, to=5.0, orient="horizontal",
                                       variable=self.param_vars["inner_rotation_speed"], command=self.update_inner_rotation)
        inner_rotation_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.inner_rotation_label = ttk.Label(parent, text=f"{self.config.visualizer.inner_rotation_speed:.2f}")
        self.inner_rotation_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Outer circle section
        ttk.Separator(parent, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1
        ttk.Label(parent, text="Outer Circle", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, pady=5)
        row += 1
        
        # Outer Min Radius
        ttk.Label(parent, text="Min Radius:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["min_radius"] = tk.DoubleVar(value=self.config.visualizer.min_radius)
        min_radius_scale = ttk.Scale(parent, from_=0.0, to=1.0, orient="horizontal",
                                   variable=self.param_vars["min_radius"], command=self.update_min_radius)
        min_radius_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.min_radius_label = ttk.Label(parent, text=f"{self.config.visualizer.min_radius:.2f}")
        self.min_radius_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Outer Max Radius
        ttk.Label(parent, text="Max Radius:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["max_radius"] = tk.DoubleVar(value=self.config.visualizer.max_radius)
        max_radius_scale = ttk.Scale(parent, from_=0.0, to=1.0, orient="horizontal",
                                   variable=self.param_vars["max_radius"], command=self.update_max_radius)
        max_radius_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.max_radius_label = ttk.Label(parent, text=f"{self.config.visualizer.max_radius:.2f}")
        self.max_radius_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Outer Bars
        ttk.Label(parent, text="Bars:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["bars"] = tk.IntVar(value=self.config.visualizer.bars)
        bars_scale = ttk.Scale(parent, from_=8, to=128, orient="horizontal",
                             variable=self.param_vars["bars"], command=self.update_bars)
        bars_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.bars_label = ttk.Label(parent, text=str(self.config.visualizer.bars))
        self.bars_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Inner circle section
        ttk.Separator(parent, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1
        ttk.Label(parent, text="Inner Circle", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, pady=5)
        row += 1
        
        # Inner Min Radius
        ttk.Label(parent, text="Min Radius:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["inner_min_radius"] = tk.DoubleVar(value=self.config.visualizer.inner_min_radius)
        inner_min_scale = ttk.Scale(parent, from_=0.0, to=1.0, orient="horizontal",
                                  variable=self.param_vars["inner_min_radius"], command=self.update_inner_min_radius)
        inner_min_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.inner_min_label = ttk.Label(parent, text=f"{self.config.visualizer.inner_min_radius:.2f}")
        self.inner_min_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Inner Max Radius
        ttk.Label(parent, text="Max Radius:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["inner_max_radius"] = tk.DoubleVar(value=self.config.visualizer.inner_max_radius)
        inner_max_scale = ttk.Scale(parent, from_=0.0, to=1.0, orient="horizontal",
                                  variable=self.param_vars["inner_max_radius"], command=self.update_inner_max_radius)
        inner_max_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.inner_max_label = ttk.Label(parent, text=f"{self.config.visualizer.inner_max_radius:.2f}")
        self.inner_max_label.grid(row=row, column=2, pady=2)
        row += 1
        
        # Inner Bars
        ttk.Label(parent, text="Bars:").grid(row=row, column=0, sticky="w", pady=2)
        self.param_vars["inner_bars"] = tk.IntVar(value=self.config.visualizer.inner_bars)
        inner_bars_scale = ttk.Scale(parent, from_=4, to=64, orient="horizontal",
                                   variable=self.param_vars["inner_bars"], command=self.update_inner_bars)
        inner_bars_scale.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        self.inner_bars_label = ttk.Label(parent, text=str(self.config.visualizer.inner_bars))
        self.inner_bars_label.grid(row=row, column=2, pady=2)
        
        # Configure column weights
        parent.columnconfigure(1, weight=1)
    
    # Parameter update methods
    def update_sensitivity(self, value):
        self.config.visualizer.sensitivity = float(value)
        self.sensitivity_label.config(text=f"{float(value):.2f}")
    
    def update_rotation(self, value):
        self.config.visualizer.rotation_speed = float(value)
        self.rotation_label.config(text=f"{float(value):.2f}")
    
    def update_inner_rotation(self, value):
        self.config.visualizer.inner_rotation_speed = float(value)
        self.inner_rotation_label.config(text=f"{float(value):.2f}")
    
    def update_min_radius(self, value):
        self.config.visualizer.min_radius = float(value)
        self.min_radius_label.config(text=f"{float(value):.2f}")
        self.recreate_visualizer()
    
    def update_max_radius(self, value):
        self.config.visualizer.max_radius = float(value)
        self.max_radius_label.config(text=f"{float(value):.2f}")
        self.recreate_visualizer()
    
    def update_bars(self, value):
        self.config.visualizer.bars = int(float(value))
        self.bars_label.config(text=str(int(float(value))))
        self.recreate_visualizer()
    
    def update_inner_min_radius(self, value):
        self.config.visualizer.inner_min_radius = float(value)
        self.inner_min_label.config(text=f"{float(value):.2f}")
        self.recreate_visualizer()
    
    def update_inner_max_radius(self, value):
        self.config.visualizer.inner_max_radius = float(value)
        self.inner_max_label.config(text=f"{float(value):.2f}")
        self.recreate_visualizer()
    
    def update_inner_bars(self, value):
        self.config.visualizer.inner_bars = int(float(value))
        self.inner_bars_label.config(text=str(int(float(value))))
        self.recreate_visualizer()
    
    def toggle_playback(self):
        """Toggle microphone playback"""
        if not PYAUDIO_AVAILABLE:
            messagebox.showerror("Error", "PyAudio is required for live mode.\nInstall with: pip install pyaudio")
            return
        
        if not self.is_playing:
            try:
                self.start_audio()
                self.is_playing = True
                self.play_button.config(text="⏸ Stop")
                self.status_var.set("Recording from microphone...")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start microphone: {e}")
        else:
            self.stop_audio()
            self.is_playing = False
            self.play_button.config(text="▶ Start")
            self.status_var.set("Stopped")
    
    def start_audio(self):
        """Start audio recording and processing"""
        # Initialize microphone
        self.audio_interface = pyaudio.PyAudio()
        self.mic_stream = self.audio_interface.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.analyzer.sample_rate,
            input=True,
            frames_per_buffer=self.analyzer.buffer_size,
            stream_callback=self.audio_callback
        )
        
        # Initialize visualizer
        self.recreate_visualizer()
        
        # Start audio thread only, display on main thread for macOS compatibility
        self.stop_flag.clear()
        self.audio_thread = threading.Thread(target=self.audio_loop, daemon=True)
        self.audio_thread.start()
        
        # Create OpenCV window on main thread
        try:
            cv2.namedWindow("Voice Viewer", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Voice Viewer", 640, 480)
        except Exception as e:
            print(f"OpenCV window creation error: {e}")
    
    def stop_audio(self):
        """Stop audio recording"""
        self.stop_flag.set()
        
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
            self.mic_stream = None
        
        if self.audio_interface:
            self.audio_interface.terminate()
            self.audio_interface = None
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Audio input callback"""
        self.audio_buffer = np.frombuffer(in_data, dtype=np.float32).copy()
        return (None, pyaudio.paContinue)
    
    def recreate_visualizer(self):
        """Recreate visualizer with current settings"""
        visualizer_class = VISUALIZERS.get("circular")
        if visualizer_class:
            self.visualizer = visualizer_class(self.config)
    
    def audio_loop(self):
        """Process audio and generate frames"""
        while not self.stop_flag.is_set():
            if self.visualizer and len(self.audio_buffer) > 0:
                try:
                    features = self.analyzer.analyze_frame(self.audio_buffer, time.time())
                    self.current_frame = self.visualizer.render_frame(features)
                except Exception:
                    pass
            time.sleep(1/20)  # 20 FPS
    
    
    def reset_params(self):
        """Reset all parameters to defaults"""
        # Reset config to theme defaults
        self.config = Config.load_theme(self.theme)
        self.config.visualizer.type = "circular"
        
        # Update GUI controls
        self.param_vars["sensitivity"].set(self.config.visualizer.sensitivity)
        self.param_vars["rotation_speed"].set(self.config.visualizer.rotation_speed)
        self.param_vars["inner_rotation_speed"].set(self.config.visualizer.inner_rotation_speed)
        self.param_vars["min_radius"].set(self.config.visualizer.min_radius)
        self.param_vars["max_radius"].set(self.config.visualizer.max_radius)
        self.param_vars["bars"].set(self.config.visualizer.bars)
        self.param_vars["inner_min_radius"].set(self.config.visualizer.inner_min_radius)
        self.param_vars["inner_max_radius"].set(self.config.visualizer.inner_max_radius)
        self.param_vars["inner_bars"].set(self.config.visualizer.inner_bars)
        
        # Update labels
        self.sensitivity_label.config(text=f"{self.config.visualizer.sensitivity:.2f}")
        self.rotation_label.config(text=f"{self.config.visualizer.rotation_speed:.2f}")
        self.inner_rotation_label.config(text=f"{self.config.visualizer.inner_rotation_speed:.2f}")
        self.min_radius_label.config(text=f"{self.config.visualizer.min_radius:.2f}")
        self.max_radius_label.config(text=f"{self.config.visualizer.max_radius:.2f}")
        self.bars_label.config(text=str(self.config.visualizer.bars))
        self.inner_min_label.config(text=f"{self.config.visualizer.inner_min_radius:.2f}")
        self.inner_max_label.config(text=f"{self.config.visualizer.inner_max_radius:.2f}")
        self.inner_bars_label.config(text=str(self.config.visualizer.inner_bars))
        
        self.recreate_visualizer()
    
    def load_config_dialog(self):
        """Show load config dialog"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.load_config(filename)
    
    def load_config(self, config_path: str):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
            
            # Apply saved visualizer settings
            visualizer_config = saved_config.get('visualizer', {})
            
            # Update config object
            for key, value in visualizer_config.items():
                if hasattr(self.config.visualizer, key):
                    setattr(self.config.visualizer, key, value)
            
            # Update GUI controls to reflect loaded values
            if 'sensitivity' in visualizer_config:
                self.param_vars["sensitivity"].set(visualizer_config['sensitivity'])
                self.sensitivity_label.config(text=f"{visualizer_config['sensitivity']:.2f}")
            
            if 'rotation_speed' in visualizer_config:
                self.param_vars["rotation_speed"].set(visualizer_config['rotation_speed'])
                self.rotation_label.config(text=f"{visualizer_config['rotation_speed']:.2f}")
                
            if 'inner_rotation_speed' in visualizer_config:
                self.param_vars["inner_rotation_speed"].set(visualizer_config['inner_rotation_speed'])
                self.inner_rotation_label.config(text=f"{visualizer_config['inner_rotation_speed']:.2f}")
            
            if 'min_radius' in visualizer_config:
                self.param_vars["min_radius"].set(visualizer_config['min_radius'])
                self.min_radius_label.config(text=f"{visualizer_config['min_radius']:.2f}")
                
            if 'max_radius' in visualizer_config:
                self.param_vars["max_radius"].set(visualizer_config['max_radius'])
                self.max_radius_label.config(text=f"{visualizer_config['max_radius']:.2f}")
                
            if 'bars' in visualizer_config:
                self.param_vars["bars"].set(visualizer_config['bars'])
                self.bars_label.config(text=str(visualizer_config['bars']))
                
            if 'inner_min_radius' in visualizer_config:
                self.param_vars["inner_min_radius"].set(visualizer_config['inner_min_radius'])
                self.inner_min_label.config(text=f"{visualizer_config['inner_min_radius']:.2f}")
                
            if 'inner_max_radius' in visualizer_config:
                self.param_vars["inner_max_radius"].set(visualizer_config['inner_max_radius'])
                self.inner_max_label.config(text=f"{visualizer_config['inner_max_radius']:.2f}")
                
            if 'inner_bars' in visualizer_config:
                self.param_vars["inner_bars"].set(visualizer_config['inner_bars'])
                self.inner_bars_label.config(text=str(visualizer_config['inner_bars']))
            
            # Recreate visualizer with new settings
            self.recreate_visualizer()
            
            messagebox.showinfo("Success", f"Configuration loaded from:\n{config_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration:\n{e}")

    def save_config_dialog(self):
        """Show save config dialog"""
        if not self.save_config_path:
            filename = filedialog.asksaveasfilename(
                title="Save Configuration",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if not filename:
                return
            self.save_config_path = filename
        
        self.save_config()
    
    def save_config(self):
        """Save current configuration"""
        try:
            config_data = {
                "theme": self.theme,
                "visualizer": {
                    "type": "circular",
                    "sensitivity": self.config.visualizer.sensitivity,
                    "rotation_speed": self.config.visualizer.rotation_speed,
                    "inner_rotation_speed": self.config.visualizer.inner_rotation_speed,
                    "min_radius": self.config.visualizer.min_radius,
                    "max_radius": self.config.visualizer.max_radius,
                    "bars": self.config.visualizer.bars,
                    "inner_min_radius": self.config.visualizer.inner_min_radius,
                    "inner_max_radius": self.config.visualizer.inner_max_radius,
                    "inner_bars": self.config.visualizer.inner_bars,
                    "smoothing": self.config.visualizer.smoothing
                }
            }
            
            with open(self.save_config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            messagebox.showinfo("Success", f"Configuration saved to:\n{self.save_config_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_playing:
            self.stop_audio()
        
        # Save config if path provided
        if self.save_config_path:
            try:
                self.save_config()
            except Exception:
                pass
        
        self.root.destroy()
    
    def update_display(self):
        """Update OpenCV display on main thread (macOS compatible)"""
        try:
            if self.current_frame is not None:
                cv2.imshow("Voice Viewer", self.current_frame)
            else:
                # Black frame with text
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Speak into microphone", (160, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.imshow("Voice Viewer", frame)
            
            # Check for ESC key
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                self.on_closing()
                return
                
        except Exception as e:
            print(f"Display update error: {e}")
        
        # Schedule next update
        if not self.stop_flag.is_set():
            self.root.after(33, self.update_display)  # ~30 FPS
    
    def run(self):
        """Run the GUI"""
        if not PYAUDIO_AVAILABLE:
            messagebox.showwarning("Warning", "PyAudio not available.\nMicrophone features will be disabled.\nInstall with: pip install pyaudio")
        
        # Force initial window update and visibility
        self.root.withdraw()  # Hide first
        self.root.deiconify()  # Then show
        self.root.update_idletasks()
        self.root.update()
        
        # Ensure all widgets are properly packed and visible
        for widget in self.root.winfo_children():
            widget.update_idletasks()
        
        # Force window to front on macOS
        try:
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after(500, lambda: self.root.attributes('-topmost', False))
            self.root.focus_force()
        except Exception:
            pass
        
        print("GUI window should now be visible. Look for 'Voice Viewer - Live Mode' window.")
        print("Window contents should include parameter sliders and controls.")
        
        # Start periodic display update on main thread
        self.update_display()
        
        self.root.mainloop()