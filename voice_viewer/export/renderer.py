"""
Video frame rendering and export functionality
"""

import cv2
import numpy as np
from typing import Iterator, Optional
from pathlib import Path
import tempfile
import os

from ..audio import AudioAnalyzer, AudioFeatures
from ..visualizers import get_visualizer
from ..config import Config


class VideoRenderer:
    """Handles video frame rendering and export"""
    
    def __init__(self, config: Config):
        self.config = config
        self.width, self.height = config.video.resolution
        self.fps = config.video.fps
        
        # Initialize components
        self.audio_analyzer = AudioAnalyzer(config.audio)
        self.visualizer = get_visualizer(config.visualizer.type, config)
    
    def render_video(self, audio_path: str, output_path: str, 
                    preview: bool = False) -> bool:
        """Render complete video from audio file"""
        try:
            # Load audio
            print(f"Loading audio: {audio_path}")
            audio, duration = self.audio_analyzer.load_audio(audio_path)
            
            if preview:
                return self._preview_mode(audio, duration)
            else:
                return self._export_mode(audio, duration, audio_path, output_path)
                
        except Exception as e:
            print(f"Error rendering video: {e}")
            return False
    
    def _export_mode(self, audio: np.ndarray, duration: float, 
                    audio_path: str, output_path: str) -> bool:
        """Export video to file"""
        try:
            # Create temporary video file
            temp_dir = tempfile.mkdtemp()
            temp_video = os.path.join(temp_dir, "temp_video.mp4")
            
            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                temp_video,
                fourcc,
                self.fps,
                (self.width, self.height)
            )
            
            if not video_writer.isOpened():
                raise RuntimeError("Failed to open video writer")
            
            print(f"Rendering {duration:.1f}s video at {self.fps}fps...")
            
            # Process audio and render frames
            frame_count = 0
            for features in self.audio_analyzer.process_audio_stream(audio, self.fps):
                frame = self.visualizer.render_frame(features)
                video_writer.write(frame)
                frame_count += 1
                
                # Progress indicator
                if frame_count % (self.fps * 5) == 0:  # Every 5 seconds
                    elapsed = frame_count / self.fps
                    print(f"  Rendered {elapsed:.1f}s / {duration:.1f}s")
            
            video_writer.release()
            print(f"Video rendering complete: {frame_count} frames")
            
            # Combine video with original audio using moviepy
            return self._combine_audio_video(temp_video, audio_path, output_path, temp_dir)
            
        except Exception as e:
            print(f"Error in export mode: {e}")
            return False
    
    def _preview_mode(self, audio: np.ndarray, duration: float) -> bool:
        """Preview mode with real-time display"""
        try:
            print(f"Previewing {duration:.1f}s audio visualization")
            print("Press 'q' to quit, 'SPACE' to pause/resume")
            
            cv2.namedWindow('Voice Viewer Preview', cv2.WINDOW_AUTOSIZE)
            
            paused = False
            frame_idx = 0
            features_list = list(self.audio_analyzer.process_audio_stream(audio, self.fps))
            
            while frame_idx < len(features_list):
                if not paused:
                    features = features_list[frame_idx]
                    frame = self.visualizer.render_frame(features)
                    
                    # Add timestamp overlay
                    timestamp_text = f"Time: {features.timestamp:.2f}s"
                    cv2.putText(frame, timestamp_text, (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    cv2.imshow('Voice Viewer Preview', frame)
                    frame_idx += 1
                
                # Handle keyboard input
                key = cv2.waitKey(int(1000 / self.fps)) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord(' '):
                    paused = not paused
                    print("Paused" if paused else "Resumed")
            
            cv2.destroyAllWindows()
            return True
            
        except Exception as e:
            print(f"Error in preview mode: {e}")
            return False
    
    def _combine_audio_video(self, video_path: str, audio_path: str, 
                           output_path: str, temp_dir: str) -> bool:
        """Combine video with original audio using FFmpeg directly"""
        try:
            # Try FFmpeg directly first (more reliable than MoviePy)
            return self._combine_with_ffmpeg(video_path, audio_path, output_path, temp_dir)
        except Exception as e:
            print(f"❌ FFmpeg approach failed: {e}")
            try:
                # Fallback to MoviePy
                return self._combine_with_moviepy(video_path, audio_path, output_path, temp_dir)
            except Exception as e2:
                print(f"❌ MoviePy fallback failed: {e2}")
                # Final fallback: copy video without audio
                import shutil
                shutil.copy2(video_path, output_path)
                shutil.rmtree(temp_dir)
                print(f"⚠️  Exported video only (no audio): {output_path}")
                return False
    
    def _combine_with_ffmpeg(self, video_path: str, audio_path: str, 
                           output_path: str, temp_dir: str) -> bool:
        """Combine audio and video using FFmpeg directly"""
        import subprocess
        import shutil
        
        print("Combining video with audio using FFmpeg...")
        
        # FFmpeg command to combine video and audio
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-i', video_path,  # video input
            '-i', audio_path,  # audio input
            '-c:v', 'copy',    # copy video stream
            '-c:a', 'aac',     # encode audio as AAC
            '-shortest',       # end when shortest input ends
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ FFmpeg export complete with audio: {output_path}")
            
            # Cleanup
            shutil.rmtree(temp_dir)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr}")
            raise e
        except FileNotFoundError:
            print("FFmpeg not found. Please install FFmpeg or use MoviePy fallback.")
            raise Exception("FFmpeg not available")
    
    def _combine_with_moviepy(self, video_path: str, audio_path: str, 
                            output_path: str, temp_dir: str) -> bool:
        """Fallback: combine using MoviePy"""
        from moviepy.editor import VideoFileClip, AudioFileClip
        import shutil
        
        print("Combining video with audio using MoviePy...")
        
        # Load video and audio
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        
        print(f"Video duration: {video.duration:.2f}s")
        print(f"Audio duration: {audio.duration:.2f}s")
        
        # Ensure audio duration matches video
        if audio.duration > video.duration:
            audio = audio.subclip(0, video.duration)
        elif audio.duration < video.duration:
            video = video.subclip(0, audio.duration)
        
        # Combine and export
        final_video = video.set_audio(audio)
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            bitrate=self.config.video.bitrate,
            verbose=False,
            logger=None
        )
        
        # Cleanup
        video.close()
        audio.close()
        final_video.close()
        shutil.rmtree(temp_dir)
        
        print(f"✅ MoviePy export complete with audio: {output_path}")
        return True