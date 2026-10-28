#!/usr/bin/env python3

from src.parser.parser import MapParser, ParsedMap
from src.solving.simulation import Simulation


def main() -> None:
    try:
        map_file: str = "maps/easy/01_linear_path.txt"
        # Parse map
        parsed_map: ParsedMap = MapParser(map_file).parse()
        # Create and run simulator
        simulator: Simulation = Simulation(parsed_map)
        simulator.plan()
        simulator.run()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
