_This project has been created as part of the 42 curriculum by pabdalla_

# Fly-in

## Description

Fly-in routes a fleet of drones from a shared start zone to an end zone through a network of connected zones. Its goal is to deliver all drones in as few simulation turns as possible while respecting zone capacities, connection capacities, and movement costs.

The project uses a custom graph, weighted pathfinding, reservations indexed by turn, and a Pygame visualizer. Drones can travel simultaneously, wait for available space, and take different routes. Graph logic is implemented without external graph libraries.

| Zone type  | Entry cost   | Behavior                                                         |
| ---------- | ------------ | ---------------------------------------------------------------- |
| Normal     | 1 turn       | Standard movement.                                               |
| Priority   | 1 turn       | Preferred when arrival times tie.                                |
| Restricted | 2 turns      | One intermediate turn on the connection, then mandatory arrival. |
| Blocked    | Inaccessible | Cannot be entered or crossed.                                    |

Start and end zones have unlimited occupancy. Other zones use `max_drones`, and each undirected connection uses `max_link_capacity` for travel in either direction.

## Instructions

Use **Python 3.10 or newer**, with `venv` and `pip` available. Run the following commands from the repository root in a Linux or WSL terminal. Graphical mode also needs a desktop display, such as WSLg when running under WSL.

1. **Create and activate a virtual environment.**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Download and install the dependencies listed in `requirements.txt`.**

   The requirements file is already included in the repository. This command installs its packages inside the activated environment:

   ```bash
   python3 -m pip install -r requirements.txt
   ```

   `pygame-ce` provides the `pygame` module. `flake8` and `mypy` provide the project's style and type checks.

3. **Run the program.**

   ```bash
   python3 src/main.py
   ```

   The visualizer opens paused. Press **Space** or click **Play** to start.

For later sessions, activate the existing environment before running the program. Use `deactivate` when finished.

### Choose a map or display mode

Edit these settings directly inside [src/main.py](src/main.py):

```python
map_file: str = "maps/hard/03_ultimate_challenge.txt"
visualize: bool = True
```

Set `map_file` to the map you want to test. Provided maps are in `maps/easy/`, `maps/medium/`, `maps/hard/`, and `maps/challenger/`; `test.txt` is also available. Paths are relative to the directory where you launch Python. No map argument is needed.

Set `visualize` to `False` for terminal-only execution. Both modes use the same planner and simulation. Terminal mode can run without a graphical display.

### Movement output

Each simulation turn produces one line of space-separated movements:

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

A token is `D<ID>-<zone>`, or `D<ID>-<connection>` during restricted-zone transit. Waiting drones are omitted. A delivered drone prints its final arrival once and produces no further movements.

Movement lines go to standard output. The delivery summary and error messages go to standard error. In graphical mode, turns are printed as playback advances; closing the window early stops playback and reports the number actually delivered.

### Development commands

After activating the environment, run the required checks with:

```bash
flake8 .
mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
```

The Makefile also provides `make install`, `make run`, `make lint`, `make lint-strict`, and `make clean`. For debugging the entry point directly, use:

```bash
python3 -m pdb src/main.py
```

## Algorithm and implementation strategy

### 1. Parse and build the graph

`MapParser` reads the drone count, zones, optional metadata, and bidirectional connections. It ignores comments and empty lines, validates the input, and reports parsing errors with their line and cause. It also checks whether the end is reachable.

`Graph` stores zones by name and keeps an adjacency list of connections. Zone subclasses implement their entry costs. `Drone` stores its identifier, position, state, and complete timed path. `Simulation` coordinates planning and playback, while `PygameVisualizer` handles the display and input.

### 2. Compute a static route cost

`shortest_path()` uses Dijkstra's algorithm with Python's `heapq`. Moving into a zone adds that destination's entry cost. Blocked zones are skipped, and equal-cost routes prefer more priority-zone entries.

The resulting route provides a base travel cost, `C`. This is a bound for later searches; drones are not forced to use this one route.

### 3. Search a timed route for each drone

`plan_drone()` searches states of the form `(zone_name, turn)`. From each state, it can:

- Wait in the same zone for one turn if space is available.
- Move to an adjacent zone, arriving after its entry cost.

The heap compares arrival turn first, then negative priority-entry count, then zone name. Before accepting a move, the planner checks destination capacity at arrival and connection capacity on every travel turn, including arrival. Restricted travel therefore reserves both connection turns and the future landing slot before takeoff.

`came_from` records predecessor states. Once the destination is reached, the planner follows these records backward and reverses the result into a chronological path.

### 4. Reserve the route and plan the next drone

`ReservationTable` counts usage with `(zone_name, turn)` and `(connection_name, turn)` keys. After choosing a complete path, `reserve_path()` books its waits, arrivals, and connection use. The next drone searches against those reservations.

Planning is sequential, but the resulting travel is simultaneous: several drones can move on the same turn when capacities allow it. Earlier routes remain fixed while later drones are planned.

If the latest planned arrival is `T`, the next search uses a horizon of `T + C`. A feasible fallback is to wait at the unlimited start until earlier drones finish, then follow the static route. This adapts the horizon to the fleet instead of imposing a fixed 500-turn limit during simulation planning.

### 5. Play back the fixed paths

`Simulation.prepare()` plans all routes and resets the fleet to turn zero. `step()` advances exactly one turn, updates waiting, moving, in-transit, and delivered states, and returns that turn's movement line. `run()` combines preparation and stepping for terminal execution.

Playback follows the stored paths without live rerouting. Restarting prepares the simulation again. The visualizer interpolates between real positions for smooth animation; animation does not change movement rules or reservations.

### Current optimization limits

Each drone gets its earliest arrival given the routes already reserved. This greedy ordering does **not** guarantee the minimum completion time for the entire fleet.

The current score does not prefer fewer moves when arrival time and priority count tie. Equal scores keep the first discovered route, so a fixed path may contain an unnecessary out-and-back trip instead of waiting. Re-entering a priority zone also earns another bonus. These behaviors come from planning, and the visualizer displays the chosen routes.

### Complexity and storage

Let `V` be the number of zones, `E` the number of connections, `D` the number of drones, and `H` the largest planning horizon.

- Static Dijkstra takes approximately `O((V + E) log V)` time.
- Each timed search can examine `O(VH)` states and `O((V + E)H)` transitions. A conservative fleet-planning bound is `O(D(V + E)H log(VH))` time.
- A conservative memory bound is `O((V + E)H + DH)`, including search data, queued alternatives, reservations, and stored drone paths.

The graph is shared across searches. Each drone's route is computed during preparation and saved for playback; paths are not recalculated every display frame. Larger fleets and longer horizons increase planning time and memory use.

## Visualization

The resizable Pygame window draws zones at their map coordinates and connects them with edges. Recognized map colors fill the nodes; outlines and markers distinguish start, end, priority, restricted, and blocked zones. Unknown color names use a fallback.

Drone icons move between their planned positions. Restricted-transit drones appear halfway along their connection on the intermediate turn. Crowded positions use a small group of icons and a badge showing the full drone count. Dense maps hide overlapping labels, while hovering reveals zone details.

The sidebar shows the current turn, total planned turns, delivered count, waiting and in-transit counts, and a zone inspector with coordinates, capacity, occupancy, color, and drone identifiers. These views help explain bottlenecks, waiting, and two-turn travel. Pause and single-step controls make individual turns easier to inspect, while zoom and pan keep larger maps readable.

| Control                         | Action                                                                |
| ------------------------------- | --------------------------------------------------------------------- |
| Space / Play button             | Play or pause; playing after completion restarts the simulation.      |
| Right arrow / Step button       | Advance one turn and pause.                                           |
| R / Restart button              | Reset the simulation to turn zero, paused.                            |
| Up / Down arrows                | Increase or decrease playback speed, from 0.25 to 8 turns per second. |
| Mouse wheel over the map        | Zoom around the cursor.                                               |
| Hold left mouse button and drag | Pan the map.                                                          |
| F / Fit map button              | Fit the complete map in the canvas.                                   |
| Hover over a zone               | Inspect its details in the sidebar.                                   |
| Escape / Window close button    | Close the visualizer.                                                 |

After all deliveries, the window stays open for inspection or restart. Terminal-only mode retains the movement log without opening Pygame.

## Resources

- [Fly-in subject](fly-in.pdf): project rules, input/output format, benchmarks, and README requirements.
- [Python virtual environments](https://docs.python.org/3/library/venv.html): creating and activating an isolated Python environment.
- [Python heapq documentation](https://docs.python.org/3/library/heapq.html): the priority queue used by Dijkstra and timed planning.
- [Pygame Community Edition documentation](https://pyga.me/docs/): window creation, drawing, fonts, input events, vectors, and timing.
- [Mypy documentation](https://mypy.readthedocs.io/en/stable/): static type checking and annotations.
- [Flake8 documentation](https://flake8.pycqa.org/en/latest/): style checks and common Python mistakes.

### AI usage

AI assistance through Codex was used to review the subject and existing code, explain the planner and its backtracking behavior, and identify integration gaps. The existing parser, graph, reservation table, and initial pathfinding code were reviewed as part of that work.

AI also assisted with extending `Drone` for timed-path playback, implementing `Simulation` and its preparation/stepping API, simplifying `main.py`, supporting direct script execution, and building the Pygame visualizer and controls. It helped add explanation comments, prepare dependencies and quality-check configuration, and write this README.

Validation assistance included capacity and movement checks, headless Pygame rendering and playback checks on Windows and WSL, and running flake8 and mypy. These checks describe the work performed; they do not establish global scheduling optimality or replace peer evaluation.
