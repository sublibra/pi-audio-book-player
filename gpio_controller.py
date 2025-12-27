"""GPIO controller with support for both real Raspberry Pi GPIO and mock mode."""
import sys
import threading
from abc import ABC, abstractmethod
from typing import Callable, List


class GPIOInterface(ABC):
    """Abstract interface for GPIO operations."""
    
    @abstractmethod
    def setup_button(self, pin: int, callback: Callable) -> None:
        """Setup a button with pull-up resistor and callback."""
        pass
    
    @abstractmethod
    def setup_led(self, pin: int) -> None:
        """Setup an LED pin."""
        pass
    
    @abstractmethod
    def set_led(self, pin: int, state: bool) -> None:
        """Set LED state (on/off)."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        pass


class RaspberryPiGPIO(GPIOInterface):
    """Real Raspberry Pi GPIO implementation using gpiozero."""
    
    def __init__(self):
        """Initialize gpiozero."""
        try:
            from gpiozero import Button, LED
            self.Button = Button
            self.LED = LED
            self.buttons = {}
            self.leds = {}
            print("Initialized Raspberry Pi GPIO (gpiozero)")
        except ImportError:
            raise RuntimeError("gpiozero not available. Use --mock flag for testing.")
    
    def setup_button(self, pin: int, callback: Callable) -> None:
        """Setup a button with pull-up resistor and callback."""
        # gpiozero Button uses pull_up=True by default, detects when_pressed
        button = self.Button(pin, pull_up=True, bounce_time=0.3)
        button.when_pressed = callback
        self.buttons[pin] = button
    
    def setup_led(self, pin: int) -> None:
        """Setup an LED pin."""
        led = self.LED(pin)
        led.off()
        self.leds[pin] = led
    
    def set_led(self, pin: int, state: bool) -> None:
        """Set LED state (on/off)."""
        if pin in self.leds:
            if state:
                self.leds[pin].on()
            else:
                self.leds[pin].off()
    
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        for button in self.buttons.values():
            button.close()
        for led in self.leds.values():
            led.close()
        print("GPIO cleanup complete")


class MockGPIO(GPIOInterface):
    """Mock GPIO implementation for testing on non-Pi systems."""
    
    def __init__(self):
        """Initialize mock GPIO."""
        self.buttons = {}
        self.leds = {}
        self.running = False
        self.input_thread = None
        print("Initialized Mock GPIO (keyboard control)")
        print("Controls: p=Play/Pause, s=Sleep, n=Next, b=Back, f=Forward, r=Rewind, q=Quit")
    
    def setup_button(self, pin: int, callback: Callable) -> None:
        """Setup a button with callback."""
        self.buttons[pin] = callback
        print(f"Mock button setup on pin {pin}")
    
    def setup_led(self, pin: int) -> None:
        """Setup an LED pin."""
        self.leds[pin] = False
        print(f"Mock LED setup on pin {pin}")
    
    def set_led(self, pin: int, state: bool) -> None:
        """Set LED state (on/off)."""
        if pin in self.leds:
            self.leds[pin] = state
            # Visual feedback in console
            led_index = list(self.leds.keys()).index(pin)
            status = "ON " if state else "OFF"
            print(f"LED {led_index + 1}: [{status}]", end="\r")
    
    def start_keyboard_control(self, button_map: dict) -> None:
        """Start keyboard input thread for simulating button presses.
        
        Args:
            button_map: Dictionary mapping key characters to GPIO pins
        """
        self.running = True
        self.button_map = button_map
        
        def input_loop():
            print("\nKeyboard controls active. Press keys to simulate buttons.")
            while self.running:
                try:
                    # Read single character (Unix-like systems)
                    import select
                    import tty
                    import termios
                    
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setcbreak(sys.stdin.fileno())
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            key = sys.stdin.read(1).lower()
                            if key in self.button_map:
                                pin = self.button_map[key]
                                if pin in self.buttons:
                                    print(f"\nButton press: {key}")
                                    self.buttons[pin]()
                            elif key == 'q':
                                print("\nQuit requested")
                                self.running = False
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except Exception as e:
                    # Fallback to simple input() for systems without termios
                    print(f"Keyboard control error: {e}")
                    break
        
        self.input_thread = threading.Thread(target=input_loop, daemon=True)
        self.input_thread.start()
    
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        self.running = False
        if self.input_thread:
            self.input_thread.join(timeout=1.0)
        print("\nMock GPIO cleanup complete")


class GPIOController:
    """Main GPIO controller that manages buttons and LEDs."""
    
    def __init__(self, gpio_pins: dict, mock_mode: bool = False):
        """Initialize GPIO controller.
        
        Args:
            gpio_pins: Dictionary with 'buttons' and 'leds' pin assignments
            mock_mode: If True, use mock GPIO instead of real hardware
        """
        self.gpio_pins = gpio_pins
        self.mock_mode = mock_mode
        
        if mock_mode:
            self.gpio = MockGPIO()
        else:
            self.gpio = RaspberryPiGPIO()
        
        self.led_pins = gpio_pins['leds']
    
    def setup_buttons(self, callbacks: dict) -> None:
        """Setup all buttons with their callbacks.
        
        Args:
            callbacks: Dictionary mapping button names to callback functions
        """
        button_pins = self.gpio_pins['buttons']
        for button_name, callback in callbacks.items():
            if button_name in button_pins:
                pin = button_pins[button_name]
                self.gpio.setup_button(pin, callback)
        
        # If mock mode, setup keyboard control
        if self.mock_mode and isinstance(self.gpio, MockGPIO):
            key_map = {
                'p': button_pins['play_pause'],
                's': button_pins['sleep_timer'],
                'n': button_pins['next_book'],
                'b': button_pins['prev_book'],
                'f': button_pins['forward'],
                'r': button_pins['backward']
            }
            self.gpio.start_keyboard_control(key_map)
    
    def setup_leds(self) -> None:
        """Setup all LED pins."""
        for pin in self.led_pins:
            self.gpio.setup_led(pin)
    
    def update_book_leds(self, active_book_index: int) -> None:
        """Update LEDs to show which book is active.
        
        Args:
            active_book_index: Index of the currently active book (0-based)
        """
        for i, pin in enumerate(self.led_pins):
            self.gpio.set_led(pin, i == active_book_index)
    
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        self.gpio.cleanup()

