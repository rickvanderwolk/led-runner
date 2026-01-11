#!/usr/bin/env python3
"""
Controller Test - Shows all controller inputs for configuration
"""

import pygame
import sys


def main():
    pygame.init()

    num_joysticks = pygame.joystick.get_count()
    if num_joysticks == 0:
        print("No controller found!")
        print("Connect a controller and try again.")
        sys.exit(1)

    # Initialize all controllers
    joysticks = []
    for i in range(num_joysticks):
        js = pygame.joystick.Joystick(i)
        js.init()
        joysticks.append(js)
        print(f"Controller {i}: {js.get_name()}")
        print(f"  Buttons: {js.get_numbuttons()}")
        print(f"  Axes: {js.get_numaxes()}")
        print(f"  Hats: {js.get_numhats()}")
        print()

    print("=" * 40)
    print("Press buttons and move d-pad to see input values")
    print("Use these values to configure config.json")
    print("Ctrl+C to quit")
    print("=" * 40)
    print()

    try:
        while True:
            pygame.event.pump()

            for idx, js in enumerate(joysticks):
                prefix = f"[Controller {idx}] " if len(joysticks) > 1 else ""

                # Check buttons
                for i in range(js.get_numbuttons()):
                    if js.get_button(i):
                        print(f"{prefix}Button {i} pressed")

                # Check axes (d-pad on SNES controllers)
                for i in range(js.get_numaxes()):
                    val = js.get_axis(i)
                    if abs(val) > 0.5:
                        direction = ""
                        if i == 0:
                            direction = " (LEFT)" if val < 0 else " (RIGHT)"
                        elif i == 1:
                            direction = " (UP)" if val < 0 else " (DOWN)"
                        print(f"{prefix}Axis {i}: {val:+.2f}{direction}")

                # Check hats (d-pad on some controllers)
                for i in range(js.get_numhats()):
                    hat = js.get_hat(i)
                    if hat != (0, 0):
                        directions = []
                        if hat[0] == -1:
                            directions.append("LEFT")
                        elif hat[0] == 1:
                            directions.append("RIGHT")
                        if hat[1] == -1:
                            directions.append("DOWN")
                        elif hat[1] == 1:
                            directions.append("UP")
                        print(f"{prefix}Hat {i}: {hat} ({'+'.join(directions)})")

            pygame.time.wait(100)

    except KeyboardInterrupt:
        print("\nDone!")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
