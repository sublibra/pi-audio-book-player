"""Audio player using madplay for playback control."""
import subprocess
import threading
import time
from typing import Optional
import os
import signal


class AudioPlayer:
    """Manages audio playback using madplay."""
    
    def __init__(self, seek_seconds: int = 60, notification_sound_path: Optional[str] = None):
        """Initialize the audio player.
        
        Args:
            seek_seconds: Number of seconds to seek forward/backward
            notification_sound_path: Path to notification sound file
        """
        self.current_file: Optional[str] = None
        self.is_playing = False
        self.is_paused = False
        self.seek_seconds = seek_seconds
        self.notification_sound_path = notification_sound_path
        self.current_position = 0.0
        self.sleep_timer_end: Optional[float] = None
        self.position_lock = threading.Lock()
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = True
        self.playback_start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.accumulated_pause_duration = 0.0
        self.process: Optional[subprocess.Popen] = None
    
    def start(self, audio_file: str, start_position: float = 0.0) -> bool:
        """Start playing an audio file.
        
        Args:
            audio_file: Path to the audio file
            start_position: Starting position in seconds
            
        Returns:
            True if started successfully, False otherwise
        """
        self.stop()
        
        try:
            if not os.path.exists(audio_file):
                print(f"Audio file not found: {audio_file}")
                return False
            
            # Build madplay command with start position if needed
            cmd = ['madplay', '-Q']
            if start_position > 0:
                # Format time as HH:MM:SS.SS
                hours = int(start_position // 3600)
                minutes = int((start_position % 3600) // 60)
                seconds = start_position % 60
                time_str = f"{hours}:{minutes:02d}:{seconds:06.3f}"
                cmd.extend(['--start', time_str])
            cmd.append(audio_file)
            
            # Start madplay process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  # Create new process group for clean killing
            )
            
            self.current_file = audio_file
            self.current_position = start_position
            self.playback_start_time = time.time() - start_position
            self.accumulated_pause_duration = 0.0
            self.is_playing = True
            self.is_paused = False
            
            # Start monitor thread
            self.monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self.monitor_thread.start()
            
            print(f"Started playback: {audio_file} at {start_position:.1f}s")
            return True
            
        except Exception as e:
            print(f"Error starting playback: {e}")
            return False
    
    def stop(self) -> None:
        """Stop playback and cleanup."""
        if self.process:
            try:
                # Kill the entire process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=2.0)
            except Exception as e:
                print(f"Error stopping process: {e}")
                try:
                    # Force kill if needed
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except:
                    pass
            self.process = None
        
        self.is_playing = False
        self.is_paused = False
        self.current_file = None
        self.playback_start_time = None
        self.pause_time = None
        self.accumulated_pause_duration = 0.0
    
    def pause(self) -> None:
        """Pause playback."""
        if self.is_playing and not self.is_paused and self.process:
            try:
                # Send SIGSTOP to pause the process
                os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
                self.is_paused = True
                self.pause_time = time.time()
                self.play_notification()
                print("Paused")
            except Exception as e:
                print(f"Error pausing: {e}")
    
    def resume(self) -> None:
        """Resume playback."""
        if self.is_playing and self.is_paused and self.process:
            try:
                # Send SIGCONT to resume the process
                os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
                if self.pause_time:
                    self.accumulated_pause_duration += time.time() - self.pause_time
                    self.pause_time = None
                self.is_paused = False
                self.play_notification()
                print("Resumed")
            except Exception as e:
                print(f"Error resuming: {e}")
    
    def toggle_play_pause(self) -> None:
        """Toggle between play and pause."""
        if self.is_playing:
            if self.is_paused:
                self.resume()
            else:
                self.pause()
    
    def seek_forward(self) -> None:
        """Seek forward by configured seconds."""
        if self.is_playing:
            # For madplay, we need to restart from new position
            with self.position_lock:
                new_pos = self.current_position + self.seek_seconds
                print(f"Seeking forward {self.seek_seconds}s to {new_pos:.1f}s")
                was_paused = self.is_paused
                self.start(self.current_file, new_pos)
                if was_paused:
                    self.pause()
    
    def seek_backward(self) -> None:
        """Seek backward by configured seconds."""
        if self.is_playing:
            # For madplay, we need to restart from new position
            with self.position_lock:
                new_pos = max(0, self.current_position - self.seek_seconds)
                print(f"Seeking backward {self.seek_seconds}s to {new_pos:.1f}s")
                was_paused = self.is_paused
                self.start(self.current_file, new_pos)
                if was_paused:
                    self.pause()
    
    def add_sleep_timer(self, minutes: int) -> None:
        """Add time to sleep timer.
        
        Args:
            minutes: Minutes to add to the sleep timer
        """
        if self.is_playing and not self.is_paused:
            current_time = time.time()
            if self.sleep_timer_end is None or self.sleep_timer_end <= current_time:
                self.sleep_timer_end = current_time + (minutes * 60)
            else:
                self.sleep_timer_end += (minutes * 60)
            
            remaining = int((self.sleep_timer_end - current_time) / 60)
            self.play_notification()
            print(f"Sleep timer set: {remaining} minutes remaining")
    
    def get_position(self) -> float:
        """Get current playback position.
        
        Returns:
            Current position in seconds
        """
        with self.position_lock:
            return self.current_position
    
    def is_active(self) -> bool:
        """Check if player is actively playing (not paused).
        
        Returns:
            True if playing and not paused
        """
        return self.is_playing and not self.is_paused
    
    def _monitor_playback(self) -> None:
        """Monitor playback and handle sleep timer."""
        while self.running and self.is_playing:
            time.sleep(0.5)
            
            # Update position based on elapsed time (excluding pause time)
            if not self.is_paused and self.playback_start_time is not None:
                current_time = time.time()
                with self.position_lock:
                    # Calculate position: elapsed time minus accumulated pause duration
                    self.current_position = (current_time - self.playback_start_time - 
                                            self.accumulated_pause_duration)
                
                # Check if process is still running
                if self.process and self.process.poll() is not None:
                    print("Playback finished")
                    self.is_playing = False
                    break
                
                # Check sleep timer
                if self.sleep_timer_end and current_time >= self.sleep_timer_end:
                    print("Sleep timer expired, pausing playback")
                    self.pause()
                    self.sleep_timer_end = None
    
    def play_announcement(self, announcement_file: str) -> bool:
        """Play an announcement file and wait for it to complete.
        
        Args:
            announcement_file: Path to the announcement audio file
            
        Returns:
            True if announcement played successfully, False otherwise
        """
        if not os.path.exists(announcement_file):
            print(f"Announcement file not found: {announcement_file}")
            return False
        
        try:
            # Play announcement using madplay and wait for completion
            print(f"Playing announcement: {announcement_file}")
            result = subprocess.run(
                ['madplay', '-Q', announcement_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30  # 30 second timeout for announcements
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("Announcement timed out")
            return False
        except Exception as e:
            print(f"Error playing announcement: {e}")
            return False
    
    def play_notification(self) -> None:
        """Play a notification sound in the background without interrupting playback."""
        if not self.notification_sound_path:
            return
        
        if not os.path.exists(self.notification_sound_path):
            print(f"Notification sound not found: {self.notification_sound_path}")
            return
        
        try:
            # Play notification in background using madplay
            subprocess.Popen(
                ['madplay', '-Q', self.notification_sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Error playing notification: {e}")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.running = False
        self.stop()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
