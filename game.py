#!/usr/bin/env python3
"""
LED Runner - Simple reaction game on an LED strip
Supports 1-4 players co-op
"""

import time
import random
import signal
import sys
import os
import pygame
import board
import neopixel
import json


class LEDGame:
    HIGHSCORE_FILE = "highscore.txt"
    FASTFORWARD_MULTIPLIER = 3  # How much faster when holding d-pad right

    # Game states
    STATE_PLAYING = 'playing'
    STATE_PAUSED = 'paused'
    STATE_GAME_OVER = 'game_over'

    def __init__(self, config_file="config.json"):
        """Initialize the game with configuration"""
        # Load configuration
        with open(config_file, 'r') as f:
            config = json.load(f)

        self.led_config = config['led']
        self.game_config = config['game']

        # GPIO pin mapping
        gpio_map = {
            12: board.D12,
            13: board.D13,
            18: board.D18,
            21: board.D21
        }

        gpio_pin = self.led_config.get('pin', 18)
        if gpio_pin not in gpio_map:
            print(f"❌ Invalid GPIO pin: {gpio_pin}")
            print(f"   Use: 12, 13, 18 or 21")
            exit(1)

        # Setup LED strip
        try:
            self.strip = neopixel.NeoPixel(
                gpio_map[gpio_pin],
                self.led_config['count'],
                brightness=self.led_config['brightness'] / 255.0,
                auto_write=False,
                pixel_order=neopixel.GRB
            )
        except Exception as e:
            print(f"❌ Error initializing LED strip: {e}")
            print(f"   Are you running the script with sudo?")
            exit(1)

        # Setup pygame
        pygame.init()

        # Start button
        self.start_button = self.game_config['buttons'].get('start', 9)

        # Base color definitions
        self.color_defs = {
            'yellow': {'rgb': (255, 255, 0), 'button': self.game_config['buttons']['yellow']},
            'red': {'rgb': (255, 0, 0), 'button': self.game_config['buttons']['red']},
            'green': {'rgb': (0, 150, 0), 'button': self.game_config['buttons']['green']},
            'blue': {'rgb': (0, 0, 255), 'button': self.game_config['buttons']['blue']}
        }

        # Detect controllers (will exit if none found)
        self.joysticks = []
        self.num_players = 0
        self.colors = {}
        self.detect_controllers(initial=True)

        # Cache player color (white)
        self.player_color = (
            self.game_config['player_color']['r'],
            self.game_config['player_color']['g'],
            self.game_config['player_color']['b']
        )

        # Initialize game
        self.running = True
        self.reset_game()
        self.state = self.STATE_PLAYING

    def detect_controllers(self, initial=False):
        """Detect and initialize controllers"""
        # Quit existing joysticks
        for js in self.joysticks:
            js.quit()

        # Re-init joystick module to detect changes
        pygame.joystick.quit()
        pygame.joystick.init()

        num_joysticks = pygame.joystick.get_count()

        if num_joysticks == 0:
            if initial:
                print("⚠️  No controller found! Connect a controller.")
                exit(1)
            else:
                print("⚠️  No controller found! Connect a controller and press START.")
                return False

        # Initialize all connected controllers (max 4)
        old_num_players = self.num_players
        self.joysticks = []
        for i in range(min(num_joysticks, 4)):
            js = pygame.joystick.Joystick(i)
            js.init()
            self.joysticks.append(js)
            print(f"🎮 Controller {i + 1}: {js.get_name()}")

        # Update player count
        self.num_players = len(self.joysticks)

        # Reassign colors
        self.colors = self.assign_colors_to_players()

        # Print mode info if changed or initial
        if initial or self.num_players != old_num_players:
            self.print_mode_info()

        return True

    def assign_colors_to_players(self):
        """Assign colors to players based on player count"""
        colors = {}

        if self.num_players == 1:
            # 1 player: all colors
            for color_name, color_def in self.color_defs.items():
                colors[color_name] = {
                    'rgb': color_def['rgb'],
                    'button': color_def['button'],
                    'player': 0
                }
        elif self.num_players == 2:
            # 2 players: P1=yellow+green (1st+3rd), P2=red+blue (2nd+4th)
            colors['yellow'] = {'rgb': self.color_defs['yellow']['rgb'], 'button': self.color_defs['yellow']['button'], 'player': 0}
            colors['red'] = {'rgb': self.color_defs['red']['rgb'], 'button': self.color_defs['red']['button'], 'player': 1}
            colors['green'] = {'rgb': self.color_defs['green']['rgb'], 'button': self.color_defs['green']['button'], 'player': 0}
            colors['blue'] = {'rgb': self.color_defs['blue']['rgb'], 'button': self.color_defs['blue']['button'], 'player': 1}
        elif self.num_players == 3:
            # 3 players: P1=yellow, P2=red, P3=green+blue
            colors['yellow'] = {'rgb': self.color_defs['yellow']['rgb'], 'button': self.color_defs['yellow']['button'], 'player': 0}
            colors['red'] = {'rgb': self.color_defs['red']['rgb'], 'button': self.color_defs['red']['button'], 'player': 1}
            colors['green'] = {'rgb': self.color_defs['green']['rgb'], 'button': self.color_defs['green']['button'], 'player': 2}
            colors['blue'] = {'rgb': self.color_defs['blue']['rgb'], 'button': self.color_defs['blue']['button'], 'player': 2}
        else:
            # 4 players: each player 1 color
            colors['yellow'] = {'rgb': self.color_defs['yellow']['rgb'], 'button': self.color_defs['yellow']['button'], 'player': 0}
            colors['red'] = {'rgb': self.color_defs['red']['rgb'], 'button': self.color_defs['red']['button'], 'player': 1}
            colors['green'] = {'rgb': self.color_defs['green']['rgb'], 'button': self.color_defs['green']['button'], 'player': 2}
            colors['blue'] = {'rgb': self.color_defs['blue']['rgb'], 'button': self.color_defs['blue']['button'], 'player': 3}

        return colors

    def print_mode_info(self):
        """Print game mode information"""
        if self.num_players == 1:
            print("\n👤 Single player mode")
            print("   (Connect more controllers for co-op)")
        elif self.num_players == 2:
            print("\n👥 Co-op mode (2 players)")
            print("   P1: 🟡 Yellow + 🟢 Green")
            print("   P2: 🔴 Red + 🔵 Blue")
        elif self.num_players == 3:
            print("\n👥 Co-op mode (3 players)")
            print("   P1: 🟡 Yellow")
            print("   P2: 🔴 Red")
            print("   P3: 🟢 Green + 🔵 Blue")
        else:
            print("\n👥 Co-op mode (4 players)")
            print("   P1: 🟡 Yellow")
            print("   P2: 🔴 Red")
            print("   P3: 🟢 Green")
            print("   P4: 🔵 Blue")

    def reset_game(self):
        """Reset all game variables for a new game"""
        self.player_pos = self.led_config['count'] // 2
        self.obstacles = []
        self.score = 0
        self.pressed_buttons = {}
        self.button_duration = 1.0
        self.obstacles_passed = 0
        self.current_difficulty = 1
        self.spawn_interval = self.led_config['count'] // 2
        self.next_spawn_at = self.led_config['count'] - 1
        self.color_history = []
        self.base_speed = 0.25
        self.current_speed = self.base_speed
        self.last_update = time.time()

    def update_display(self):
        """Update the LED strip with current game state"""
        self.strip.fill((0, 0, 0))

        for obs in self.obstacles:
            if 0 <= obs['pos'] < self.led_config['count']:
                self.strip[obs['pos']] = obs['color']

        if len(self.pressed_buttons) == 0:
            self.strip[self.player_pos] = self.player_color

        self.strip.show()

    def show_pause_display(self):
        """Show pause indicator - blinking game state"""
        t = time.time()

        if int(t * 2) % 2 == 0:
            self.strip.fill((0, 0, 0))
            for obs in self.obstacles:
                if 0 <= obs['pos'] < self.led_config['count']:
                    self.strip[obs['pos']] = obs['color']
            self.strip[self.player_pos] = self.player_color
        else:
            self.strip.fill((0, 0, 0))
            for obs in self.obstacles:
                if 0 <= obs['pos'] < self.led_config['count']:
                    r, g, b = obs['color']
                    self.strip[obs['pos']] = (r // 4, g // 4, b // 4)

        self.strip.show()

    def show_animation(self, color, duration=1.0, blink_count=3):
        """Show a blink animation on all LEDs"""
        blink_duration = duration / (blink_count * 2)
        anim_color = (color['r'], color['g'], color['b'])

        for _ in range(blink_count):
            self.strip.fill(anim_color)
            self.strip.show()
            time.sleep(blink_duration)

            self.strip.fill((0, 0, 0))
            self.strip.show()
            time.sleep(blink_duration)

    def show_score_digits(self):
        """Show score as digits with color coding (10 LEDs per digit)"""
        self.strip.fill((0, 0, 0))

        color_zero = (200, 0, 200)
        digits = [int(d) for d in str(self.score)]

        total_leds = self.led_config['count']
        max_digits = total_leds // 10

        colors_palette = [
            (255, 255, 0),
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
        ]

        for pos, digit in enumerate(digits):
            if pos >= max_digits:
                break

            start_led = pos * 10

            if digit == 0:
                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds and i % 2 == 0:
                        self.strip[led_idx] = color_zero
            else:
                color_bright = colors_palette[pos % 4]
                for i in range(10):
                    led_idx = start_led + i
                    if led_idx < total_leds and i < digit:
                        self.strip[led_idx] = color_bright

        self.strip.show()

    def load_highscore(self):
        """Load highscore from file, return 0 if not exists"""
        if os.path.exists(self.HIGHSCORE_FILE):
            try:
                with open(self.HIGHSCORE_FILE, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, IOError):
                return 0
        return 0

    def save_highscore(self, score):
        """Save highscore to file"""
        with open(self.HIGHSCORE_FILE, 'w') as f:
            f.write(str(score))

    def show_highscore_effect(self):
        """Show colorful rainbow effect for new highscore"""
        colors = [
            (255, 0, 0),      # Red
            (255, 127, 0),    # Orange
            (255, 255, 0),    # Yellow
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
            (75, 0, 130),     # Indigo
            (148, 0, 211),    # Violet
        ]

        # Rainbow wave effect - 3 waves
        for wave in range(3):
            for offset in range(self.led_config['count'] + len(colors)):
                self.strip.fill((0, 0, 0))
                for i, color in enumerate(colors):
                    pos = offset - i * 2
                    if 0 <= pos < self.led_config['count']:
                        self.strip[pos] = color
                self.strip.show()
                time.sleep(0.02)

        # Flash all colors
        for _ in range(3):
            for color in colors:
                self.strip.fill(color)
                self.strip.show()
                time.sleep(0.1)

        self.strip.fill((0, 0, 0))
        self.strip.show()

    def press_button(self, player_idx, button, color_name):
        """Register button press for a specific player"""
        key = (player_idx, button)
        self.pressed_buttons[key] = time.time()

        if self.num_players > 1:
            print(f"P{player_idx + 1} {color_name.upper()}!")
        else:
            print(f"🎮 {color_name.upper()}!")

    def is_button_pressed(self, required_player, button):
        """Check if the correct player has the button pressed"""
        if self.num_players == 1:
            for (player_idx, btn), _ in self.pressed_buttons.items():
                if btn == button:
                    return True
            return False

        key = (required_player, button)
        return key in self.pressed_buttons

    def is_fastforward_held(self):
        """Check if any controller has fast-forward button held"""
        fastforward_btn = self.game_config['buttons'].get('fastforward')
        for js in self.joysticks:
            # Check configured button (for SNES controllers)
            if fastforward_btn is not None and js.get_button(fastforward_btn):
                return True
            # Also check hat/d-pad (for other controllers)
            if js.get_numhats() > 0:
                hat = js.get_hat(0)
                if hat[0] == 1:  # Right on d-pad
                    return True
        return False

    def get_available_colors(self):
        """Return available colors based on score and player count"""
        if self.num_players == 1:
            # Single player: progressive unlock
            if self.score >= 18:
                return ['yellow', 'red', 'green', 'blue']
            elif self.score >= 12:
                return ['yellow', 'red', 'green']
            elif self.score >= 6:
                return ['yellow', 'red']
            else:
                return ['yellow']
        elif self.num_players == 2:
            # 2 players: P1=yellow+green, P2=red+blue (unlock order)
            if self.score >= 6:
                return ['yellow', 'red', 'green', 'blue']
            elif self.score >= 3:
                return ['yellow', 'red', 'green']
            else:
                return ['yellow', 'red']
        elif self.num_players == 3:
            # 3 players: start with 1 each, P3 gets second color later
            if self.score >= 6:
                return ['yellow', 'red', 'green', 'blue']
            else:
                return ['yellow', 'red', 'green']
        else:
            # 4 players: all colors from start
            return ['yellow', 'red', 'green', 'blue']

    def update_difficulty(self):
        """Update difficulty level based on score"""
        if self.score <= 2:
            new_difficulty = 1
        elif self.score <= 5:
            new_difficulty = 2
        elif self.score <= 9:
            new_difficulty = 3
        elif self.score <= 14:
            new_difficulty = 4
        elif self.score <= 20:
            new_difficulty = 5
        else:
            new_difficulty = 5 + ((self.score - 20) // 8)

        if new_difficulty > self.current_difficulty:
            self.current_difficulty = new_difficulty
            self.spawn_interval = max(3, self.led_config['count'] // self.current_difficulty)
            self.current_speed = max(0.05, self.base_speed - (self.current_difficulty * 0.015))

            print(f"⚡ Level {self.current_difficulty}!")

        # Announce new colors based on player count
        available = self.get_available_colors()
        if self.num_players == 1:
            if len(available) == 2 and self.score == 6:
                print(f"🎨 +Red!")
            elif len(available) == 3 and self.score == 12:
                print(f"🎨 +Green!")
            elif len(available) == 4 and self.score == 18:
                print(f"🎨 +Blue!")
        elif self.num_players == 2:
            if len(available) == 3 and self.score == 3:
                print(f"🎨 +Green (P1)!")
            elif len(available) == 4 and self.score == 6:
                print(f"🎨 +Blue (P2)!")
        elif self.num_players == 3:
            if len(available) == 4 and self.score == 6:
                print(f"🎨 +Blue (P3)!")

    def spawn_obstacle(self):
        """Spawn a new obstacle"""
        spawn_pos = self.led_config['count'] - 1

        for obs in self.obstacles:
            if obs['pos'] == spawn_pos:
                return

        available_colors = self.get_available_colors()
        color_name = random.choice(available_colors)
        color_data = self.colors[color_name]

        obstacle = {
            'pos': spawn_pos,
            'color': color_data['rgb'],
            'button': color_data['button'],
            'player': color_data['player'],
            'color_name': color_name
        }

        self.obstacles.append(obstacle)
        self.next_spawn_at = obstacle['pos'] - self.spawn_interval

    def game_over(self):
        """Handle game over"""
        print(f"❌ Game Over! Score: {self.score}")

        self.show_animation(self.game_config['fail_color'], 1.0, 3)

        # Check for highscore
        highscore = self.load_highscore()
        is_new_highscore = self.score > highscore

        if is_new_highscore:
            print(f"\n{'='*40}")
            print(f"🎉 NEW HIGHSCORE: {self.score}!")
            print(f"{'='*40}")
            self.show_highscore_effect()
            self.save_highscore(self.score)
        else:
            print(f"\n{'='*40}")
            print(f"🏆 FINAL SCORE: {self.score}")
            print(f"   Highscore: {highscore}")
            print(f"{'='*40}")

        print(f"\nPress START for new game...")

        self.show_score_digits()
        self.state = self.STATE_GAME_OVER

    def handle_input(self):
        """Process controller input from all players"""
        pygame.event.pump()

        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                joy_id = event.joy

                # Ignore controllers beyond player count
                if joy_id >= self.num_players:
                    continue

                # Start button (any controller)
                if event.button == self.start_button:
                    if self.state == self.STATE_PLAYING:
                        self.state = self.STATE_PAUSED
                        print("\n⏸️  PAUSED")
                    elif self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING
                        self.last_update = time.time()
                        print("\n▶️  RESUMED")
                    elif self.state == self.STATE_GAME_OVER:
                        # Re-detect controllers for new game
                        print("\n🔄 Checking controllers...")
                        self.detect_controllers()
                        self.reset_game()
                        self.state = self.STATE_PLAYING
                        print("🎮 New game!")

                # Color buttons (only when playing)
                elif self.state == self.STATE_PLAYING:
                    for color_name, color_data in self.colors.items():
                        if event.button == color_data['button']:
                            required_player = color_data['player']

                            if self.num_players == 1:
                                self.press_button(joy_id, event.button, color_name)
                            elif joy_id == required_player:
                                self.press_button(joy_id, event.button, color_name)
                            break

    def update_obstacles(self):
        """Move all obstacles and check collision"""
        current_time = time.time()
        expired = [key for key, press_time in self.pressed_buttons.items()
                   if current_time - press_time > self.button_duration]
        for key in expired:
            del self.pressed_buttons[key]

        for obs in self.obstacles:
            obs['pos'] -= 1

        if len(self.obstacles) == 0 or self.obstacles[-1]['pos'] <= self.next_spawn_at:
            self.spawn_obstacle()

        for obs in self.obstacles[:]:
            if obs['pos'] == self.player_pos:
                required_player = obs['player']
                if self.is_button_pressed(required_player, obs['button']):
                    if self.num_players > 1:
                        print(f"✅ P{required_player + 1} {obs['color_name'].upper()}")
                    else:
                        print(f"✅ {obs['color_name'].upper()}")
                    self.color_history.append(obs['color'])
                else:
                    if self.num_players > 1:
                        print(f"💥 P{required_player + 1} missed {obs['color_name'].upper()}!")
                    else:
                        print(f"💥 Missed {obs['color_name'].upper()}!")
                    self.game_over()
                    return

        before_count = len(self.obstacles)
        self.obstacles = [obs for obs in self.obstacles if obs['pos'] >= 0]
        obstacles_passed = before_count - len(self.obstacles)

        if obstacles_passed > 0:
            self.obstacles_passed += obstacles_passed
            self.score += 1
            print(f"Score: {self.score}")
            self.update_difficulty()

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.strip.fill((0, 0, 0))
        self.strip.show()
        pygame.quit()

    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\n👋 Signal {signum} received, shutting down...")
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Main game loop"""
        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        print("\n🎮 LED Runner")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("START = Pause / Resume / New game")
        print("D-PAD RIGHT = Fast-forward (hold)")
        print("\nGame starting...")
        print("CTRL+C to quit\n")

        try:
            while self.running:
                self.handle_input()

                if self.state == self.STATE_PLAYING:
                    current_time = time.time()
                    # Apply fast-forward if d-pad right is held
                    effective_speed = self.current_speed
                    if self.is_fastforward_held():
                        effective_speed = self.current_speed / self.FASTFORWARD_MULTIPLIER
                    if current_time - self.last_update >= effective_speed:
                        self.update_obstacles()
                        self.last_update = current_time
                    if self.state == self.STATE_PLAYING:
                        self.update_display()

                elif self.state == self.STATE_PAUSED:
                    self.show_pause_display()

                elif self.state == self.STATE_GAME_OVER:
                    pass

                time.sleep(0.01)

        except KeyboardInterrupt:
            print(f"\n\n👋 Stopped. Score: {self.score}")
        finally:
            self.cleanup()


if __name__ == "__main__":
    game = LEDGame()
    game.run()
