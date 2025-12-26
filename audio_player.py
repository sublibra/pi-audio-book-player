"""Audio player using mpg123 subprocess for playback control."""
import subprocess
import threading
import time
from typing import Optional
import os


class AudioPlayer:
    """Manages audio playback using mpg123."""
    
    def __init__(self, seek_seconds: int = 60):
        """Initialize the audio player.
        
        Args:
            seek_seconds: Number of seconds to seek forward/backward
        """
        self.process: Optional[subprocess.Popen] = None
        self.current_file: Optional[str] = None
        self.is_playing = False
        self.is_paused = False
        self.seek_seconds = seek_seconds
        self.current_position = 0.0
        self.sleep_timer_end: Optional[float] = None
        self.position_lock = threading.Lock()
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = True
    
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
            # Build mpg123 command with remote control mode
            cmd = ['mpg123', '-R']
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.current_file = audio_file
            self.current_position = start_position
            self.is_playing = True
            self.is_paused = False
            
            # Load the file
            self._send_command(f'LOAD {audio_file}')
            
            # Seek to start position if needed
            if start_position > 0:
                self._send_command(f'JUMP {int(start_position)}s')
            
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
                self._send_command('QUIT')
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            finally:
                self.process = None
        
        self.is_playing = False
        self.is_paused = False
        self.current_file = None
    
    def pause(self) -> None:
        """Pause playback."""
        if self.is_playing and not self.is_paused:
            self._send_command('PAUSE')
            self.is_paused = True
            print("Paused")
    
    def resume(self) -> None:
        """Resume playback."""
        if self.is_playing and self.is_paused:
            self._send_command('PAUSE')
            self.is_paused = False
            print("Resumed")
    
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
            self._send_command(f'JUMP +{self.seek_seconds}s')
            with self.position_lock:
                self.current_position += self.seek_seconds
            print(f"Seeking forward {self.seek_seconds}s")
    
    def seek_backward(self) -> None:
        """Seek backward by configured seconds."""
        if self.is_playing:
            self._send_command(f'JUMP -{self.seek_seconds}s')
            with self.position_lock:
                self.current_position = max(0, self.current_position - self.seek_seconds)
            print(f"Seeking backward {self.seek_seconds}s")
    
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
    
    def _send_command(self, command: str) -> None:
        """Send a command to mpg123 via stdin.
        
        Args:
            command: Command string to send
        """
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + '\n')
                self.process.stdin.flush()
            except Exception as e:
                print(f"Error sending command '{command}': {e}")
    
    def _monitor_playback(self) -> None:
        """Monitor playback and handle sleep timer."""
        last_update = time.time()
        
        while self.running and self.is_playing:
            time.sleep(0.5)
            
            # Update position estimate (simple increment, not frame-accurate)
            if not self.is_paused:
                current_time = time.time()
                elapsed = current_time - last_update
                with self.position_lock:
                    self.current_position += elapsed
                last_update = current_time
                
                # Check sleep timer
                if self.sleep_timer_end and current_time >= self.sleep_timer_end:
                    print("Sleep timer expired, pausing playback")
                    self.pause()
                    self.sleep_timer_end = None
            else:
                last_update = time.time()
    
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
            # Play announcement and wait for it to complete
            print(f"Playing announcement: {announcement_file}")
            process = subprocess.Popen(
                ['mpg123', announcement_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.wait()
            return True
            
        except Exception as e:
            print(f"Error playing announcement: {e}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.running = False
        self.stop()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

