# Fly-in — Project Prep Notes

## 1. What this project actually is

Strip away the drone theme and this is a **multi-agent, time-windowed pathfinding and scheduling problem** on a weighted graph, with:
- Per-node (zone) capacity limits
- Per-edge (connection) capacity limits
- Variable, sometimes multi-turn, edge traversal costs
- A hard constraint that "in-flight" drones can't be interrupted
- A strict OOP + typesafe implementation, no graph libraries

The two hardest parts are (1) building your own graph/pathfinding from scratch, and (2) turning single-drone paths into a **conflict-free, capacity-respecting schedule** for many drones moving at once. Everything else (parsing, OOP structure, visuals) is comparatively mechanical.

---

## 2. Key Concepts You Need

### 2.1 Graph representation (from scratch)
Since `networkx`/`graphlib` are banned, you need your own model:
- `Zone` (node): name, coordinates, type (`normal`/`restricted`/`priority`/`blocked`), color, `max_drones`
- `Connection` (edge): the two zones it links, `max_link_capacity`
- `Graph` (or `Network`): owns all zones + connections, exposes neighbor lookup

Use an **adjacency list** (dict of `zone -> list[Connection]`), not an adjacency matrix — sparser, easier to extend with metadata per edge.

### 2.2 Weighted shortest path (Dijkstra's algorithm)
Because zone types give different entry costs (`normal`=1, `restricted`=2, `priority`=1 but "preferred", `blocked`=∞/impassable), a plain BFS (which assumes uniform edge weight) is not enough. You need **Dijkstra's algorithm**:
- Priority queue keyed by accumulated cost
- Cost of moving into a zone = the cost of *that destination zone's type*
- `blocked` zones are simply excluded from the graph traversal (never added as reachable neighbors)
- "Priority" zones aren't cheaper, they're just *preferred when costs tie* — you'll want a tie-breaking rule (e.g., prefer priority zones, or fewer total restricted zones) rather than baking it into the cost function

Complexity: O((V + E) log V) per single-drone path computation with a binary heap.

### 2.3 The real challenge: multi-agent scheduling with capacity
A shortest path for *one* drone isn't a solution — you have N drones that must share limited zone/connection capacity without colliding. This is the core "algorithm" the subject keeps asking you to justify.

The standard mental model is a **time-expanded graph** (a.k.a. space-time graph):
- Instead of nodes being just "zones", think of nodes as `(zone, turn)` pairs
- A drone occupies exactly one `(zone, turn)` at a time
- Two drones conflict if they'd occupy the same `(zone, turn)` beyond that zone's `max_drones`, or traverse the same `(connection, turn)` beyond its `max_link_capacity`
- Scheduling becomes: assign each drone a sequence of `(zone, turn)` steps such that no capacity constraint is ever violated

You don't need to build a literal time-expanded graph data structure (though you can) — many students instead simulate turn-by-turn:
1. Compute a base path (or ranked candidate paths) per drone using Dijkstra
2. At each simulated turn, try to advance every drone one step
3. Before committing a move, check destination zone capacity and connection capacity for *that turn*
4. If blocked, the drone waits (stays in place) or is rerouted
5. Repeat until all drones reach `end`

This turn-by-turn greedy/priority scheduling approach is legitimate and matches what the subject calls "strategic waiting" and "avoidance of path conflicts." For harder maps, you may need smarter conflict resolution — this is effectively a simplified version of **Conflict-Based Search (CBS)**, a known technique in multi-agent pathfinding (MAPF) literature, if you want to go further than greedy scheduling.

### 2.4 Restricted-zone "commit" mechanic
Moving into a `restricted` zone costs 2 turns, and the drone **cannot wait mid-transit** — once it commits to that connection, it must land exactly 2 turns later. This means:
- You need a state for "drone is currently in-flight on connection X, arriving in N more turns"
- That drone occupies the *connection's* capacity for the full transit, not the destination zone's capacity until it actually lands
- The scheduler must reserve the destination slot in advance (or handle the arrival-turn capacity check knowing it's already committed) — an in-flight drone has no way to divert or hold, so you must not commit a drone to a restricted-zone connection unless you're confident the destination will have room when it arrives

### 2.5 Deadlock avoidance
With shared capacity and waiting drones, it's possible for two drones to wait on each other forever (classic deadlock). Think about how you detect/avoid this:
- Ordering/priority rules for who moves first when there's contention
- Reserving destination slots before committing a move
- A "no live drones moved this turn but not all delivered" check as a deadlock detector/fallback

### 2.6 OOP design
The subject requires **fully object-oriented** design. Suggested class breakdown:
- `Zone` (maybe subclassed per type, or a `ZoneType` enum + strategy for cost) — subclassing (`NormalZone`, `RestrictedZone`, `PriorityZone`, `BlockedZone`) each implementing an `entry_cost()` method is a clean way to demonstrate polymorphism, which peer reviewers will likely ask about
- `Connection`
- `Graph` / `Network`
- `Drone` (id, current position, state: `waiting` / `moving` / `in_transit` / `delivered`)
- `Parser` (reads file → builds `Graph` + drone count, raises custom exceptions on bad input)
- `Scheduler` / `Simulator` (owns the turn loop, capacity bookkeeping, conflict resolution)
- `Visualizer` (colored terminal output and/or graphical display) — kept separate from simulation logic
- Custom exception classes (e.g., `ParseError`, `InvalidZoneTypeError`) rather than bare `ValueError`s everywhere, so you can report "line X: cause Y" cleanly

### 2.7 Parser design
- Read line by line, track line numbers for error messages
- Strip `#` comments
- Split `zone` / `connection` metadata brackets `[...]` into key=value pairs; order inside brackets is not guaranteed
- Validate as you go rather than after: unknown zone type → immediate error with line number, duplicate connection → error, connection referencing an undefined zone → error
- Enforce exactly one `start_hub` and one `end_hub`

### 2.8 Typing and linting discipline
- `mypy --strict` (or at least the mandatory flag set) means every function needs full type hints, including `-> None` returns and typed containers (`list[Drone]`, not bare `list`)
- `flake8` will catch unused imports, line length, etc. — run it continuously, not just at the end
- Use `try/except` around file I/O and parsing; use context managers (`with open(...) as f`) for file handles

### 2.9 Output format
Each simulation turn = one line of space-separated `D<id>-<destination>` tokens (zone name, or connection name if mid-transit toward a restricted zone). Drones that don't move that turn are simply omitted from the line — don't print "stay" tokens.

---

## 3. Task List

**Phase 0 — Setup**
- [ ] Init git repo, `.gitignore`, virtual environment
- [ ] Scaffold `Makefile` with `install`, `run`, `debug`, `clean`, `lint`, `lint-strict`
- [ ] Decide project layout (see suggested tree below)

**Phase 1 — Data model & parser**
- [ ] Implement `Zone` hierarchy (or enum + cost strategy) with `entry_cost()`
- [ ] Implement `Connection`, `Graph`
- [ ] Implement custom parser exceptions with line/cause reporting
- [ ] Implement parser: read `nb_drones`, zones, connections; validate types, duplicate connections, undefined zone refs, malformed metadata
- [ ] Write your own extra test map files (edge cases: missing start/end, blocked start, self-loop connection, unknown zone type, duplicate names)

**Phase 2 — Single-drone pathfinding**
- [ ] Implement Dijkstra over your `Graph` (respecting `blocked` as impassable, `restricted`=2, `normal`/`priority`=1)
- [ ] Implement a tie-breaking preference toward `priority` zones
- [ ] Unit test against the example map in the subject

**Phase 3 — Multi-drone scheduler**
- [ ] Design the turn-by-turn simulation loop (or time-expanded graph, your choice)
- [ ] Implement zone occupancy checks (`max_drones`, start/end exceptions)
- [ ] Implement connection occupancy checks (`max_link_capacity`)
- [ ] Implement the restricted-zone "committed 2-turn transit, no waiting mid-flight" state
- [ ] Implement waiting/staying-in-place logic
- [ ] Implement deadlock avoidance / detection
- [ ] Produce the turn-by-turn `D<id>-<zone/connection>` output log

**Phase 4 — Visualization**
- [ ] Pick terminal-color output (e.g., ANSI codes or a lightweight lib) and/or a graphical option (tkinter/pygame/matplotlib)
- [ ] Show zone states and drone positions per turn

**Phase 5 — Quality pass**
- [ ] Add type hints everywhere, run `mypy` (mandatory flags, then try `--strict`)
- [ ] Run `flake8`, fix violations
- [ ] Write `pytest`/`unittest` coverage for parser edge cases, Dijkstra correctness, capacity conflicts, restricted-zone commit logic
- [ ] Re-check exception handling around all file/resource use

**Phase 6 — Benchmark against provided targets**
- [ ] Run all provided easy/medium/hard maps, compare turn counts to the reference targets in §VII.7
- [ ] Tune scheduling heuristics if you're missing targets (e.g., better drone ordering, path diversity across disjoint routes)

**Phase 7 — Docs**
- [ ] Write `README.md`: italic first line with logins, Description, Instructions, Resources (+ AI usage disclosure), algorithm-choice write-up, visualization write-up
- [ ] Be ready to explain and defend every line — no unreviewed AI-generated blocks (per Chapter II)

**Phase 8 — Bonus (optional, only after mandatory is 100%)**
- [ ] Hit every reference benchmark exactly ("perfectly")
- [ ] Attempt the Challenger map (25 drones, beat 45-turn reference)

---

## 4. Requirements Recap

- Python **3.10+**, `flake8`-clean, `mypy`-clean (mandatory flag set at minimum)
- **No graph libraries** (`networkx`, `graphlib`, etc. forbidden) — everything hand-rolled
- **Fully object-oriented**
- Type hints on all functions/params/returns/variables where applicable
- Docstrings (PEP 257, Google or NumPy style)
- Graceful exception handling everywhere; a crash during review = non-functional
- Context managers for any resource (files, etc.)
- `Makefile` with `install`, `run`, `debug`, `clean`, `lint`, optional `lint-strict`
- `.gitignore`, everything at repo root
- Visual feedback: colored terminal and/or graphical
- Output format exactly as specified (space-separated `D<id>-<dest>` per turn line, omit non-movers)
- `README.md` per Chapter VIII's exact structure, in English
- Be prepared to explain/modify your code live during peer review

---

## 5. Suggested File Tree

```
fly-in/
├── Makefile
├── README.md
├── .gitignore
├── requirements.txt
├── maps/
│   ├── easy_1.txt ... (provided + your own)
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── zone.py          # Zone base + subclasses / ZoneType
│   │   ├── connection.py
│   │   ├── graph.py
│   │   └── drone.py
│   ├── parser/
│   │   ├── map_parser.py
│   │   └── errors.py        # custom exceptions
│   ├── pathfinding/
│   │   └── dijkstra.py
│   ├── simulation/
│   │   └── scheduler.py     # turn loop, capacity/conflict logic
│   └── visualization/
│       └── terminal_view.py # (and/or graphical_view.py)
└── tests/
    ├── test_parser.py
    ├── test_pathfinding.py
    └── test_scheduler.py
```

---

## 6. Things to Decide Before You Start Coding

1. **Zone cost/behavior**: subclassing (`RestrictedZone(Zone)`) vs. a single `Zone` class with a `ZoneType` enum + strategy object? Subclassing shows cleaner polymorphism for peer review, but a strategy/enum table is easier to extend if new zone types are added mid-project.
2. **Scheduling approach**: literal time-expanded graph vs. turn-by-turn greedy simulation with reservations. The latter is simpler to reason about and debug; the former is more "provably correct" but heavier to implement under a deadline.
3. **Drone ordering policy**: when multiple drones want the same slot, who wins? (e.g., shortest remaining path first, FIFO by drone id, or path-diversity-first to spread drones across disjoint routes early)
4. **Visualization**: terminal-only is faster to implement and satisfies the requirement; graphical is more impressive but costs more time — decide based on how much of the benchmark-chasing you want to prioritize.

## Classes structure

- `models/zone.py` — Zone (ABC) + all four subclasses (NormalZone, PriorityZone, RestrictedZone, BlockedZone) together, since they're small and tightly related — splitting each into its own file would just mean four tiny files you constantly jump between
- `models/connection.py` — Connection alone
models/graph.py — Graph alone (it's the most complex of the group)
- `models/drone.py` — Drone + its DroneState enum together
- `parser/errors.py` — ParseError + subclasses together
- `parser/map_parser.py` — MapParser + ParsedMap together (parser and its result type are tightly coupled)


## Time Estimate (~95–135 hours total)

| Phase | Task | Hours |
|---|---|---|
| 0 | Setup + fully reading/understanding the subject before coding | 3–5 |
| 1 | Data model + parser + custom exceptions + your own test maps | 15–20 |
| 2 | Dijkstra pathfinding, single-drone | 10–15 |
| 3 | Multi-drone scheduler (reservations, capacity, restricted-zone commit, deadlocks) | 30–40 |
| 4 | Visualization (terminal color) | 6–10 |
| 5 | Type hints, mypy/flake8, tests | 10–15 |
| 6 | Benchmarking + tuning | 8–12 |
| 7 | README | 2–3 |
| Buffer | Getting stuck, re-reading, rewriting a bad first attempt | 10–15 |

**Notes:**
- Phase 3 is the real project — everything else is a variant of skills from earlier 42 projects.
- Get Phases 1–2 fully tested before starting Phase 3, so bugs don't blur across layers.
- Skip graphical visualization unless there's time left over; terminal color output satisfies the requirement.
- Ignore the bonus (Challenger map) until the mandatory part is fully working and clean — it isn't reviewed otherwise.