"""State manager for saving and loading audiobook playback state."""
import json
import os
from typing import Optional


class StateManager:
    """Manages persistent state for audiobook playback."""
    
    def __init__(self, state_file: str):
        """Initialize the state manager.
        
        Args:
            state_file: Path to the JSON file for storing state
        """
        self.state_file = state_file
        self.current_book_index = 0
        self.current_position = 0.0
        self.load_state()
    
    def load_state(self) -> None:
        """Load state from file if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.current_book_index = data.get('book_index', 0)
                    self.current_position = data.get('position', 0.0)
                    print(f"Loaded state: Book {self.current_book_index + 1}, Position {self.current_position:.1f}s")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading state: {e}")
                self.current_book_index = 0
                self.current_position = 0.0
        else:
            print("No saved state found, starting fresh")
    
    def save_state(self) -> None:
        """Save current state to file."""
        try:
            data = {
                'book_index': self.current_book_index,
                'position': self.current_position
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving state: {e}")
    
    def set_book(self, book_index: int) -> None:
        """Set the current book index.
        
        Args:
            book_index: Index of the book (0-based)
        """
        self.current_book_index = book_index
        self.current_position = 0.0
        self.save_state()
    
    def set_position(self, position: float) -> None:
        """Set the current playback position.
        
        Args:
            position: Position in seconds
        """
        self.current_position = max(0.0, position)
    
    def get_book(self) -> int:
        """Get the current book index.
        
        Returns:
            Current book index (0-based)
        """
        return self.current_book_index
    
    def get_position(self) -> float:
        """Get the current playback position.
        
        Returns:
            Position in seconds
        """
        return self.current_position

