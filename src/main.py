#!/usr/bin/env python3

from src.parser.parser import MapParser, ParsedMap
from src.solving.simulation import Simulation


def main() -> None:
    """Choose a map here, plan its fleet, and open the selected display."""
    try:
        map_file: str = "maps/challenger/01_the_impossible_dream.txt"
        visualize: bool = True
        # Parse map
        parsed_map: ParsedMap = MapParser(map_file).parse()
        # Plan every route once before opening the window or printing turns.
        simulator: Simulation = Simulation(parsed_map)
        simulator.plan()
        if visualize:
            from src.visualization.pygame_visualizer import PygameVisualizer
            PygameVisualizer(simulator).run()
        else:
            simulator.run()

        # Closing the window early must report only drones actually delivered.
        delivered = sum(d.current_zone is simulator.end
                        for d in simulator.drones)
        print(f"Delivered {delivered} drones in {simulator.turn} turns.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
