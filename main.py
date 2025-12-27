#!/usr/bin/env python3
"""
Main entry point for the Raspberry Pi Audiobook Player.
"""
import argparse
import json
import signal
import sys
import time
import threading
from typing import List, Dict

from audio_player import AudioPlayer
from gpio_controller import GPIOController
from state_manager import StateManager


class AudiobookPlayer:
    """Main audiobook player application."""
    
    def __init__(self, config: dict, mock_mode: bool = False):
        """Initialize the audiobook player.
        
        Args:
            config: Configuration dictionary
            mock_mode: If True, run in mock mode for testing
        """
        self.config = config
        self.mock_mode = mock_mode
        self.running = True
        
        # Initialize components
        self.state_manager = StateManager(config['state_file'])
        self.audio_player = AudioPlayer(
            seek_seconds=config['seek_seconds'],
            notification_sound_path=config.get('notification_sound_path')
        )
        self.gpio_controller = GPIOController(config['gpio_pins'], mock_mode=mock_mode)
        
        self.audiobooks: List[Dict[str, str]] = config['audiobooks']
        self.save_interval = config['save_interval_seconds']
        self.sleep_timer_minutes = config['sleep_timer_minutes']
        self.book_announcement_path = config.get('book_announcement_path', 'announcements')
        
        # Setup GPIO
        self._setup_gpio()
        
        # Start state saving thread
        self.save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self.save_thread.start()
        
        # Start playing last audiobook
        self._start_current_book()
    
    def _setup_gpio(self) -> None:
        """Setup GPIO buttons and LEDs."""
        # Setup button callbacks
        callbacks = {
            'play_pause': self._on_play_pause,
            'sleep_timer': self._on_sleep_timer,
            'next_book': self._on_next_book,
            'prev_book': self._on_prev_book,
            'forward': self._on_forward,
            'backward': self._on_backward
        }
        
        self.gpio_controller.setup_buttons(callbacks)
        self.gpio_controller.setup_leds()
        self.gpio_controller.update_book_leds(self.state_manager.get_book())
    
    def _start_current_book(self) -> None:
        """Start playing the current book from saved position."""
        book_index = self.state_manager.get_book()
        position = self.state_manager.get_position()
        
        if 0 <= book_index < len(self.audiobooks):
            book = self.audiobooks[book_index]
            print(f"\nStarting: {book['name']}")
            self.audio_player.start(book['path'], position)
            self.gpio_controller.update_book_leds(book_index)
        else:
            print(f"Invalid book index: {book_index}")
    
    def _on_play_pause(self) -> None:
        """Handle play/pause button press."""
        print("\n[Button] Play/Pause")
        self.audio_player.toggle_play_pause()
        # Save state after play/pause
        current_position = self.audio_player.get_position()
        self.state_manager.set_position(current_position)
        self.state_manager.save_state()
    
    def _on_sleep_timer(self) -> None:
        """Handle sleep timer button press."""
        print(f"\n[Button] Sleep Timer (+{self.sleep_timer_minutes} min)")
        self.audio_player.add_sleep_timer(self.sleep_timer_minutes)
    
    def _on_next_book(self) -> None:
        """Handle next book button press."""
        print("\n[Button] Next Book")
        current_book = self.state_manager.get_book()
        next_book = (current_book + 1) % len(self.audiobooks)
        self._switch_book(next_book)
        # State is saved in _switch_book
    
    def _on_prev_book(self) -> None:
        """Handle previous book button press."""
        print("\n[Button] Previous Book")
        current_book = self.state_manager.get_book()
        prev_book = (current_book - 1) % len(self.audiobooks)
        self._switch_book(prev_book)
        # State is saved in _switch_book
    
    def _on_forward(self) -> None:
        """Handle forward button press."""
        print("\n[Button] Forward")
        self.audio_player.seek_forward()
        # Save state after seeking
        current_position = self.audio_player.get_position()
        self.state_manager.set_position(current_position)
        self.state_manager.save_state()
    
    def _on_backward(self) -> None:
        """Handle backward button press."""
        print("\n[Button] Backward")
        self.audio_player.seek_backward()
        # Save state after seeking
        current_position = self.audio_player.get_position()
        self.state_manager.set_position(current_position)
        self.state_manager.save_state()
    
    def _switch_book(self, book_index: int) -> None:
        """Switch to a different audiobook.
        
        Args:
            book_index: Index of the book to switch to
        """
        if 0 <= book_index < len(self.audiobooks):
            # Save current position first
            current_position = self.audio_player.get_position()
            self.state_manager.set_position(current_position)
            self.state_manager.save_state()
            
            # Switch to new book
            self.state_manager.set_book(book_index)
            book = self.audiobooks[book_index]
            print(f"Switching to: {book['name']}")
            
            # Play book announcement (file named {book_index + 1}.mp3)
            announcement_file = f"{self.book_announcement_path}/{book_index + 1}.mp3"
            self.audio_player.play_announcement(announcement_file)
            
            # Start new book from beginning
            self.audio_player.start(book['path'], 0.0)
            self.gpio_controller.update_book_leds(book_index)
    
    def _auto_save_loop(self) -> None:
        """Automatically save state at regular intervals."""
        while self.running:
            time.sleep(self.save_interval)
            
            if self.audio_player.is_active():
                current_position = self.audio_player.get_position()
                self.state_manager.set_position(current_position)
                self.state_manager.save_state()
    
    def cleanup(self) -> None:
        """Cleanup resources before exit."""
        print("\n\nShutting down...")
        self.running = False
        
        # Save final state
        if self.audio_player.is_active():
            current_position = self.audio_player.get_position()
            self.state_manager.set_position(current_position)
            self.state_manager.save_state()
        
        # Cleanup components
        self.audio_player.cleanup()
        self.gpio_controller.cleanup()
        
        print("Shutdown complete")


def load_config(config_file: str) -> dict:
    """Load configuration from JSON file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Raspberry Pi Audiobook Player')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode for testing')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Create player
    player = AudiobookPlayer(config, mock_mode=args.mock)
    
    # Setup signal handlers for clean shutdown
    def signal_handler(sig, frame):
        player.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep running
    print("\nAudiobook Player running...")
    print("Press Ctrl+C to exit\n")
    
    try:
        while player.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        player.cleanup()


if __name__ == '__main__':
    main()

