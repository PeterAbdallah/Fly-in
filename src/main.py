#!/usr/bin/env python3
"""Choose a map here and run the fleet in a window or in the terminal."""

# sys provides the import search path, stderr, and the process exit code.
# Path finds this file's location without assuming a Windows or Linux path.
import sys
from pathlib import Path

# Let "python3 src/main.py" find the src package in the project root.
# Direct execution has no package context and initially searches inside src/.
# With "python3 -m src.main", Python already knows the package's parent.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Parsing produces the graph and fleet size; Simulation owns the moving fleet.
from src.parser.errors import ParseError
from src.parser.parser import MapParser
from src.solving.simulation import Simulation


def main() -> int:
    """Read the chosen map and run its drones until they are delivered."""
    # Change this filename to choose the map you want to test.
    # Example: "maps/easy/01_linear_path.txt"
    # Relative filenames are resolved from the directory you run Python in.
    map_file: str = "maps/hard/03_ultimate_challenge.txt"
    # Set this to False if you want to test using terminal output only.
    # Both modes use the same planner, reservations, and drone state updates.
    visualize: bool = True

    try:
        # Read the file, validate it, and build the graph and drone count.
        parsed_map = MapParser(map_file).parse()

        # Create the map's drones at the start zone with shared reservations.
        simulation = Simulation(parsed_map.graph, parsed_map.nb_drones)

        if visualize:
            # Load Pygame only when requested; Space starts/pauses playback.
            # Keeping this import here lets terminal mode run without Pygame.
            # The window plans all paths first, then advances on turn ticks.
            from src.visualization.pygame_visualizer import PygameVisualizer
            PygameVisualizer(simulation).run()
        else:
            # The same simulation can still print every turn in the terminal.
            # A line lists only moving drones; waiting drones are omitted.
            for movements in simulation.run():
                print(movements)
    except (ParseError, ValueError, RuntimeError) as error:
        # Show input, planning, or window errors without a traceback.
        print(f"Error: {error}", file=sys.stderr)
        return 1

    # Closing the window early may leave some drones undelivered.
    # True counts as 1 in sum(), so count drones actually at the end zone.
    delivered = sum(drone.current_zone is simulation.end
                    for drone in simulation.drones)
    # Show the result on stderr so stdout contains only the movement lines.
    # This lets you redirect stdout to a clean simulation log if needed.
    print(
        f"Delivered {delivered} drones "
        f"in {simulation.turn} turns.",
        file=sys.stderr,
    )
    # Zero tells the terminal that the program finished successfully.
    return 0


# Run main when this file is launched, and pass its exit code to the shell.
if __name__ == "__main__":
    raise SystemExit(main())
