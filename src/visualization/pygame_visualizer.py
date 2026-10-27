"""Draw the map and play its planned drone movements in a Pygame window.

Simulation owns the real paths, turns, and drone states. This module reads
those states and adds playback controls, a camera, and decorative animation.
"""

import math
import os

from src.models.drone import Drone, DroneState
from src.models.zone import BlockedZone, PriorityZone, RestrictedZone, Zone
from src.solving.simulation import Simulation

# Keep Pygame's startup greeting out of the simulation's movement log.
if "PYGAME_HIDE_SUPPORT_PROMPT" not in os.environ:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

try:
    import pygame
except ImportError as error:
    # main imports this module only for graphical playback, so terminal-only
    # runs can work without Pygame. Explain how to install it when requested.
    raise RuntimeError(
        "Pygame is missing. Install dependencies with "
        "python3 -m pip install -r requirements.txt"
    ) from error


# Pygame accepts red/green/blue values from 0 to 255. Keep the interface's
# palette together so a zone type uses the same color in the map and legend.
RGB = tuple[int, int, int]
BACKGROUND: RGB = (12, 18, 29)
PANEL: RGB = (19, 28, 43)
GRID: RGB = (27, 38, 55)
TEXT: RGB = (229, 236, 247)
MUTED: RGB = (144, 162, 187)
ACCENT: RGB = (90, 210, 242)
GREEN: RGB = (82, 214, 160)
PURPLE: RGB = (170, 155, 255)
ORANGE: RGB = (248, 178, 94)
RED: RGB = (241, 114, 133)
# Repeating colors keep drone identities stable across turns and restarts.
DRONE_COLORS: tuple[RGB, ...] = (
    ACCENT, ORANGE, PURPLE, GREEN, RED, (242, 224, 139),
)


class PygameVisualizer:
    """Show the real simulation state with playback and camera controls."""

    def __init__(self, simulation: Simulation) -> None:
        """Store playback settings; the window opens only when run() starts."""
        # Share the existing Simulation; do not create a separate fleet for
        # the screen. Start paused so the user can inspect the initial map.
        self.simulation = simulation
        self.width, self.height = 1280, 800
        self.playing = False
        # speed measures turns per second. elapsed accumulates time until a
        # whole turn is due; animation measures visual progress from 0 to 1.
        self.speed = 1.0
        self.elapsed = 0.0
        self.animation = 1.0

        # origin is the screen position of map coordinate (0, 0), and scale
        # is pixels per map unit. fit_scale remembers the fitted zoom level.
        self.origin = pygame.Vector2()
        self.scale = 1.0
        self.fit_scale = 1.0
        # Mouse position serves both hover inspection and zoom anchoring;
        # dragging determines whether mouse motion should move the camera.
        self.mouse = pygame.Vector2()
        self.dragging = False
        # Placeholder rectangles become the actual screen areas in _layout.
        self.canvas = pygame.Rect(0, 0, 1, 1)
        self.sidebar = pygame.Rect(0, 0, 1, 1)
        self.buttons: dict[str, pygame.Rect] = {}

        # Remember the last real positions for visual interpolation only.
        # Drawing between them never changes a drone's timed path or state.
        self.previous: dict[int, pygame.Vector2] = {}
        # Type declarations describe objects created later in _setup(); the
        # constructor therefore does not open a window or initialize fonts.
        self.screen: pygame.Surface
        self.font: pygame.font.Font
        self.small_font: pygame.font.Font
        self.title_font: pygame.font.Font
        self.large_font: pygame.font.Font

    def _setup(self) -> None:
        """Initialize graphics, prepare the fleet, and fit the whole map."""
        # Only graphics and fonts are needed; do not initialize sound devices.
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode(
            (self.width, self.height), pygame.RESIZABLE
        )
        pygame.display.set_caption("Fly-in | Drone visualizer")
        # Font(None, size) uses Pygame's bundled font, avoiding extra assets.
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 19)
        self.title_font = pygame.font.Font(None, 38)
        self.large_font = pygame.font.Font(None, 46)
        # Plan before playback, then lay out the screen before fitting the
        # camera: fitting needs the canvas dimensions from _layout().
        self._restart()
        self._layout()
        self._fit_map()

    def _layout(self) -> None:
        """Reserve separate areas for the graph, information, and buttons."""
        # Pixel margins leave a header above, controls below, and a fixed
        # sidebar on the right; only the map area grows with extra width.
        self.canvas = pygame.Rect(20, 104, self.width - 340, self.height - 198)
        self.sidebar = pygame.Rect(self.width - 300, 104, 280,
                                   self.height - 198)
        # Store button rectangles once for both drawing and mouse hit tests.
        self.buttons = {
            name: pygame.Rect(20 + index * 106, self.height - 68, 96, 42)
            for index, name in enumerate(("play", "step", "restart", "fit"))
        }

    def _fit_map(self) -> None:
        """Center the coordinates and choose a scale that fits every zone."""
        zones = list(self.simulation.graph.zones.values())
        min_x, max_x = min(z.x for z in zones), max(z.x for z in zones)
        min_y, max_y = min(z.y for z in zones), max(z.y for z in zones)
        # Leave 56 pixels on each side for nodes, labels, and drone icons.
        # Choose the smaller axis scale to fit both axes without stretching.
        # A span of one avoids division by zero on horizontal/vertical maps.
        self.scale = min(
            (self.canvas.width - 112) / max(1, max_x - min_x),
            (self.canvas.height - 112) / max(1, max_y - min_y),
        )
        self.fit_scale = self.scale
        # Map Y grows upward, while screen Y grows downward. Negating the
        # map center's Y matches _point(), then origin centers that result.
        center = pygame.Vector2((min_x + max_x) / 2, -(min_y + max_y) / 2)
        self.origin = pygame.Vector2(self.canvas.center) - center * self.scale

    def _point(self, world: pygame.Vector2) -> pygame.Vector2:
        """Convert map coordinates into a point on the screen."""
        # Invert Y, scale map units into pixels, then apply camera panning.
        return pygame.Vector2(world.x, -world.y) * self.scale + self.origin

    def _zone_point(self, zone: Zone) -> pygame.Vector2:
        """Return the screen position of a zone."""
        # Centralize the conversion so hubs, links, and hover tests agree.
        return self._point(pygame.Vector2(zone.x, zone.y))

    def _drone_world(self, drone: Drone) -> pygame.Vector2:
        """Place a drone in a zone or at its transit connection's midpoint."""
        # Return map coordinates here; camera zoom and pan happen afterward.
        if drone.current_zone is not None:
            return pygame.Vector2(drone.current_zone.x, drone.current_zone.y)
        connection = drone.current_connection
        if connection is not None:
            # A restricted entry lasts two turns. Its intermediate state is
            # on the link, so use the midpoint until the arrival turn.
            return pygame.Vector2(
                (connection.zone_a.x + connection.zone_b.x) / 2,
                (connection.zone_a.y + connection.zone_b.y) / 2,
            )
        # A safe visual fallback for an unpositioned drone is the start hub.
        return pygame.Vector2(self.simulation.start.x, self.simulation.start.y)

    def _restart(self) -> None:
        """Reset reservations, paths, drone states, and the playback clock."""
        # prepare() resets the actual fleet, not just the displayed counter.
        self.simulation.prepare()
        self.playing = False
        self.elapsed = 0.0
        self.animation = 1.0
        # Both ends of the next animation initially match the start state,
        # so restarting cannot interpolate from the previous finished run.
        self.previous = {
            drone.drone_id: self._drone_world(drone)
            for drone in self.simulation.drones
        }

    def _step(self) -> None:
        """Advance one turn and preserve the subject's terminal output."""
        # Capture positions before step() changes the real drone states.
        self.previous = {
            drone.drone_id: self._drone_world(drone)
            for drone in self.simulation.drones
        }
        movements = self.simulation.step()
        # None means finished; an empty string still represents a valid
        # all-waiting turn and must produce its own output line.
        if movements is not None:
            print(movements, flush=True)
            self.animation = 0.0
        if self.simulation.turn >= self.simulation.total_turns:
            # Stop autoplay at completion; _update still finishes animation.
            self.playing = False

    def _command(self, action: str) -> None:
        """Use the same playback commands for buttons and keyboard events."""
        if action == "play":
            # Playing a completed schedule starts a new run automatically.
            if self.simulation.turn == self.simulation.total_turns:
                self._restart()
            self.playing = not self.playing
            # A fresh play/pause command starts a full turn interval.
            self.elapsed = 0.0
            if not self.playing:
                # Pausing exposes the exact current state immediately.
                self.animation = 1.0
        elif action == "step":
            # Manual stepping always pauses automatic advancement first.
            self.playing = False
            self.elapsed = 0.0
            self._step()
            # Manual stepping shows the exact state immediately.
            self.animation = 1.0
        elif action == "restart":
            self._restart()
        elif action == "fit":
            # Fitting moves only the camera; the current turn is unchanged.
            self._fit_map()

    def _zoom(self, factor: float) -> None:
        """Zoom around the mouse so the hovered part of the map stays put."""
        # Undo the current camera transform to find the point under the
        # cursor. Its Y is already in the inverted screen coordinate system.
        world = (self.mouse - self.origin) / self.scale
        # Clamp relative to the fitted view so zoom stays useful on maps
        # with very different coordinate ranges, and never reaches zero.
        self.scale = max(self.fit_scale * 0.3,
                         min(self.fit_scale * 10, self.scale * factor))
        # Reposition the origin to keep that same point under the cursor.
        self.origin = self.mouse - world * self.scale

    def _events(self) -> bool:
        """Handle closing, resizing, playback keys, and mouse navigation."""
        # Drain all queued input every frame. False asks run() to exit;
        # all other events leave the window running.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.VIDEORESIZE:
                # Keep room for the sidebar on smaller windows.
                self.width = max(1000, event.w)
                self.height = max(720, event.h)
                self.screen = pygame.display.set_mode(
                    (self.width, self.height), pygame.RESIZABLE
                )
                self._layout()
                # Refit after resizing so the full map remains reachable.
                self._fit_map()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                # Map keys to the same actions used by clickable buttons.
                actions = {
                    pygame.K_SPACE: "play", pygame.K_RIGHT: "step",
                    pygame.K_r: "restart", pygame.K_f: "fit",
                }
                if event.key in actions:
                    self._command(actions[event.key])
                elif event.key == pygame.K_UP:
                    # Doubling provides simple speed steps, capped at 8.
                    self.speed = min(8.0, self.speed * 2)
                elif event.key == pygame.K_DOWN:
                    # Keep a positive minimum so playback can still advance.
                    self.speed = max(0.25, self.speed / 2)
            elif event.type == pygame.MOUSEMOTION:
                self.mouse.update(event.pos)
                if self.dragging:
                    # event.rel is a pixel displacement, matching origin.
                    self.origin += pygame.Vector2(event.rel)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse.update(event.pos)
                # Buttons consume the click before it can start a map drag.
                for action, rect in self.buttons.items():
                    if rect.collidepoint(event.pos):
                        self._command(action)
                        break
                else:
                    # This for/else runs only when no button was clicked.
                    self.dragging = self.canvas.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # Stop dragging even if the release is outside the canvas.
                self.dragging = False
            elif event.type == pygame.MOUSEWHEEL:
                # Ignore wheel input over the sidebar. Positive wheel steps
                # multiply scale by 1.15; negative steps divide it equally.
                if self.canvas.collidepoint(self.mouse):
                    self._zoom(1.15 ** event.y)
        return True

    def _update(self, seconds: float) -> None:
        """Animate between states and advance the simulation on turn ticks."""
        # Visual travel lasts a quarter of a turn interval. At 1, icons have
        # reached their actual state; this can finish after autoplay stops.
        self.animation = min(1.0, self.animation + seconds * self.speed * 4)
        if self.playing:
            # Convert frame seconds into fractions of a simulation turn.
            self.elapsed += seconds * self.speed
            if self.elapsed >= 1.0:
                # Keep the unused fraction so frame timing does not drift.
                self.elapsed -= 1.0
                self._step()

    def _text(self, text: str, position: tuple[float, float],
              color: RGB = TEXT, small: bool = False) -> None:
        """Draw a label using the normal or smaller interface font."""
        # Render creates a text image; blit copies it to the screen. True
        # enables antialiasing to smooth the text's edges.
        font = self.small_font if small else self.font
        self.screen.blit(font.render(text, True, color), position)

    def _zone_color(self, zone: Zone) -> RGB:
        """Keep endpoints and zone types recognizable beside map colors."""
        # Type colors belong to outlines and markers. Metadata can still
        # color a hub's fill without hiding its role in the graph.
        if zone is self.simulation.start:
            return GREEN
        if zone is self.simulation.end:
            return PURPLE
        if isinstance(zone, BlockedZone):
            return RED
        if isinstance(zone, RestrictedZone):
            return ORANGE
        if isinstance(zone, PriorityZone):
            return ACCENT
        return MUTED

    def _hovered_zone(self) -> Zone | None:
        """Find a nearby zone only while the mouse is over the map."""
        closest: Zone | None = None
        # This tolerance is in screen pixels, keeping hover easy at any zoom.
        distance_limit = 24.0
        if self.canvas.collidepoint(self.mouse):
            # Dense maps can have several nearby zones; select the nearest.
            for zone in self.simulation.graph.zones.values():
                distance = self._zone_point(zone).distance_to(self.mouse)
                if distance < distance_limit:
                    closest = zone
                    distance_limit = distance
        return closest

    def _draw_links(self) -> None:
        """Draw bidirectional connections and highlight restricted transit."""
        # Only drones currently between hubs have current_connection set;
        # one-turn moves are already represented at their destination hub.
        active = {
            drone.current_connection.name for drone in self.simulation.drones
            if drone.current_connection is not None
        }
        for connection in self.simulation.graph.connections:
            a = self._zone_point(connection.zone_a)
            b = self._zone_point(connection.zone_b)
            busy = connection.name in active
            pygame.draw.line(self.screen, ACCENT if busy else (55, 71, 94),
                             a, b, 3 if busy else 2)
            # Capacity labels need enough zoom to avoid cluttering dense maps.
            if self.scale > 100 and connection.max_link_capacity > 1:
                middle = (a + b) / 2
                self._text(f"x{connection.max_link_capacity}",
                           (middle.x + 5, middle.y + 5), MUTED, True)

    def _draw_zones(self, hovered: Zone | None) -> None:
        """Draw colored nodes; hide overlapping names on dense maps."""
        # Grow hubs with zoom but bound their pixel radius for visibility
        # when zoomed out and readability when zoomed far in.
        radius = max(9, min(19, int(self.scale * 0.18)))
        labels: list[pygame.Rect] = []
        zones = self.simulation.graph.zones.values()
        # Important names get first choice of label space.
        ordered = sorted(zones, key=lambda z: (
            z is not hovered,
            z not in (self.simulation.start, self.simulation.end),
        ))
        for zone in ordered:
            point = self._zone_point(zone)
            border = self._zone_color(zone)
            # Arbitrary valid color names may not exist in Pygame's palette.
            try:
                color = pygame.Color(zone.color) if zone.color else None
            except ValueError:
                color = None
            # Darken the metadata color to leave the outline/marker legible.
            fill = ((color.r // 3, color.g // 3, color.b // 3)
                    if color is not None else GRID)
            pygame.draw.circle(self.screen, fill, point, radius)
            pygame.draw.circle(self.screen, border, point, radius, 2)
            if zone is hovered:
                # A separate ring identifies the hub shown in the inspector.
                pygame.draw.circle(self.screen, TEXT, point, radius + 4, 1)

            marker = ""
            # Short markers remain useful when full names are hidden. Start
            # and end take precedence over the zone's movement type.
            if zone is self.simulation.start:
                marker = "S"
            elif zone is self.simulation.end:
                marker = "E"
            elif isinstance(zone, BlockedZone):
                marker = "X"
            elif isinstance(zone, RestrictedZone):
                marker = "2"
            elif isinstance(zone, PriorityZone):
                marker = "P"
            label = self.small_font.render(marker, True, border)
            self.screen.blit(label, label.get_rect(center=point))

            important = zone in (hovered, self.simulation.start,
                                 self.simulation.end)
            # Ordinary names are hidden below 80 pixels per map unit; the
            # important names can still compete for available label space.
            if not important and self.scale < 80:
                continue
            label = self.small_font.render(zone.name, True, TEXT)
            rect = label.get_rect(midtop=(point.x, point.y + radius + 7))
            # Keep labels inside the map and remember accepted rectangles
            # so later names cannot overlap them.
            rect.clamp_ip(self.canvas.inflate(-8, -8))
            if not any(rect.colliderect(other) for other in labels):
                pygame.draw.rect(self.screen, PANEL, rect.inflate(6, 3),
                                 border_radius=3)
                self.screen.blit(label, rect)
                labels.append(rect)

    def _draw_drones(self) -> None:
        """Draw small quadcopters, grouping large crowds with a count badge."""
        # Group by actual map position, not animated pixels: drones sharing
        # a hub or link midpoint should share one count badge.
        groups: dict[tuple[float, float], list[Drone]] = {}
        for drone in self.simulation.drones:
            delivered = drone.state is DroneState.DELIVERED
            # Animate the last arrival, then remove the delivered drone.
            arriving = drone.path[-1][1] == self.simulation.turn
            if delivered and not (arriving and self.animation < 1.0):
                continue
            world = self._drone_world(drone)
            groups.setdefault((world.x, world.y), []).append(drone)

        radius = max(9, min(19, int(self.scale * 0.18))) + 12
        for group in groups.values():
            # Limit each group to six decorative icons; the badge still
            # reports every drone, avoiding a pile of overlapping sprites.
            visible = group[:6]
            for index, drone in enumerate(visible):
                target = self._drone_world(drone)
                before = self.previous.get(drone.drone_id, target)
                # lerp interpolates from the previous real position to the
                # current one. It does not choose or alter a route.
                point = self._point(before.lerp(target, self.animation))
                # Spread icons around the hub with evenly spaced angles.
                # These offsets are decoration, not extra zones or movement.
                angle = index * math.tau / len(visible) - math.pi / 2
                point += pygame.Vector2(math.cos(angle),
                                        math.sin(angle)) * radius
                color = DRONE_COLORS[(drone.drone_id - 1) % len(DRONE_COLORS)]
                # Four rotors distinguish drones from the circular hubs.
                for dx, dy in ((-4, -4), (4, 4), (-4, 4), (4, -4)):
                    rotor = point + pygame.Vector2(dx, dy)
                    pygame.draw.line(self.screen, color, point, rotor, 2)
                    pygame.draw.circle(self.screen, color, rotor, 2)
                pygame.draw.circle(self.screen, TEXT, point, 3)
                if len(group) == 1 and self.scale >= 80:
                    # Show IDs only when their text has room to be readable.
                    self._text(f"D{drone.drone_id}",
                               (point.x + 9, point.y - 7), color, True)
            if len(group) > 1:
                # The count stays beside the actual shared position, even
                # while the decorative icons animate toward it.
                point = self._point(self._drone_world(group[0]))
                badge = pygame.Rect(point.x + 15, point.y - 30, 30, 21)
                pygame.draw.rect(self.screen, ACCENT, badge, border_radius=6)
                label = self.small_font.render(str(len(group)), True,
                                               BACKGROUND)
                self.screen.blit(label, label.get_rect(center=badge.center))

    def _draw_sidebar(self, hovered: Zone | None) -> None:
        """Show progress, controls, a type legend, and hovered zone details."""
        pygame.draw.rect(self.screen, PANEL, self.sidebar, border_radius=12)
        # Confine long inspector text to its panel instead of the graph.
        self.screen.set_clip(self.sidebar)
        x, y = self.sidebar.x + 20, self.sidebar.y + 20
        drones = self.simulation.drones
        # Read current DroneState values so the sidebar matches the actual
        # simulation, including waits and restricted-zone transit.
        delivered = sum(d.state is DroneState.DELIVERED for d in drones)
        transit = sum(d.state is DroneState.IN_TRANSIT for d in drones)
        waiting = sum(d.state is DroneState.WAITING for d in drones)
        self._text("SIMULATION TURN", (x, y), MUTED, True)
        label = self.large_font.render(
            f"{self.simulation.turn} / {self.simulation.total_turns}",
            True, TEXT,
        )
        self.screen.blit(label, (x, y + 24))
        self._text(f"{delivered} of {len(drones)} delivered",
                   (x, y + 78), GREEN)
        track = pygame.Rect(x, y + 109, 240, 5)
        pygame.draw.rect(self.screen, GRID, track, border_radius=2)
        progress = delivered / max(1, len(drones))
        pygame.draw.rect(self.screen, GREEN,
                         (x, y + 109, int(240 * progress), 5), border_radius=2)
        self._text(f"{transit} in transit     {waiting} waiting",
                   (x, y + 130), MUTED, True)

        self._text("ZONE TYPES", (x, y + 172), MUTED, True)
        # Alternate columns with % 2, moving down a row every two entries.
        for index, (name, color) in enumerate((
            ("Normal", MUTED), ("Priority", ACCENT),
            ("Restricted: 2", ORANGE), ("Blocked", RED),
        )):
            left = x + (index % 2) * 128
            top = y + 205 + (index // 2) * 26
            pygame.draw.circle(self.screen, color, (left + 5, top + 5), 5, 2)
            self._text(name, (left + 16, top - 2), TEXT, True)

        self._text("CONTROLS", (x, y + 264), MUTED, True)
        # Keep controls visible while playback runs so no help dialog is
        # needed to inspect or navigate the simulation.
        for index, text in enumerate((
            "Space  play / pause", "Right  next turn   |   R  restart",
            "Up / Down  playback speed",
            "Wheel  zoom  |  Drag  pan  |  F  fit",
        )):
            self._text(text, (x, y + 290 + index * 20), MUTED, True)

        # Keep every inspector row visible at the minimum window height.
        self._text("ZONE INSPECTOR", (x, y + 370), MUTED, True)
        if hovered is None:
            self._text("Hover a zone for details.", (x, y + 400), TEXT, True)
        else:
            # Delivered drones disappear from active occupancy displays.
            present = [d for d in drones if d.current_zone is hovered
                       and d.state is not DroneState.DELIVERED]
            capacity = ("unlimited" if hovered in (
                self.simulation.start, self.simulation.end
            ) else str(hovered.max_drones))
            # Keep the ID list short enough for the fixed-width sidebar;
            # the suffix tells how many additional drones share the hub.
            ids = ", ".join(f"D{d.drone_id}" for d in present[:4]) or "none"
            if len(present) > 4:
                ids += f" +{len(present) - 4}"
            details = (
                hovered.name,
                f"{type(hovered).__name__}  ({hovered.x}, {hovered.y})",
                f"Occupancy: {len(present)} / {capacity}",
                f"Color: {hovered.color or 'default'}", f"Drones: {ids}",
            )
            for index, text in enumerate(details):
                self._text(text, (x, y + 395 + index * 21), TEXT, True)
        # Later footer drawing must not inherit the sidebar's clip rectangle.
        self.screen.set_clip(None)

    def _draw_footer(self) -> None:
        """Draw clickable controls and a turn-progress timeline."""
        # Only the play button's label changes with playback state.
        labels = {"play": "Pause" if self.playing else "Play",
                  "step": "Step", "restart": "Restart", "fit": "Fit map"}
        for action, rect in self.buttons.items():
            # A lighter fill acknowledges hover; an outline marks Play.
            color = (35, 57, 78) if rect.collidepoint(self.mouse) else PANEL
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            if action == "play":
                pygame.draw.rect(self.screen, ACCENT, rect, 1, border_radius=8)
            label = self.font.render(labels[action], True, TEXT)
            self.screen.blit(label, label.get_rect(center=rect.center))
        x = self.buttons["fit"].right + 24
        self._text("PLAYBACK", (x, self.height - 72), MUTED, True)
        self._text(f"{self.speed:g} turn/s",
                   (self.width - 110, self.height - 72), ACCENT, True)
        width = self.width - x - 20
        # This timeline measures elapsed turns; the sidebar's progress bar
        # instead measures delivered drones. max(1, ...) avoids zero division.
        progress = self.simulation.turn / max(1, self.simulation.total_turns)
        pygame.draw.rect(self.screen, GRID,
                         (x, self.height - 42, width, 7), border_radius=3)
        pygame.draw.rect(self.screen, ACCENT,
                         (x, self.height - 42, int(width * progress), 7),
                         border_radius=3)

    def _draw(self) -> None:
        """Render the graph and UI without changing any simulation state."""
        # Redraw from a clean background each frame to erase old positions.
        self.screen.fill(BACKGROUND)
        title = self.title_font.render("FLY-IN", True, TEXT)
        self.screen.blit(title, (24, 23))
        self._text("Drone routing / flight overview", (148, 34), MUTED)
        graph = self.simulation.graph
        self._text(
            f"{len(graph.zones)} zones / {len(graph.connections)} connections",
            (24, 72), MUTED, True,
        )
        status = "PLAYING" if self.playing else "PAUSED"
        if self.simulation.turn == self.simulation.total_turns:
            # Completion takes precedence over the ordinary paused label.
            status = "ALL DELIVERED"
        self._text(status, (self.width - 180, 35), GREEN if self.playing
                   or status == "ALL DELIVERED" else ACCENT)

        pygame.draw.rect(self.screen, PANEL, self.canvas, border_radius=12)
        # Clip the graph so panning cannot paint over the sidebar or buttons.
        self.screen.set_clip(self.canvas)
        # The dotted grid is screen decoration, not additional map nodes.
        for x in range(self.canvas.left + 20, self.canvas.right, 40):
            for y in range(self.canvas.top + 20, self.canvas.bottom, 40):
                pygame.draw.circle(self.screen, GRID, (x, y), 1)
        hovered = self._hovered_zone()
        # Draw back to front: connections, hubs, then drone icons on top.
        self._draw_links()
        self._draw_zones(hovered)
        self._draw_drones()
        self.screen.set_clip(None)
        # Remove the map clip before drawing the independent UI panels.
        self._draw_sidebar(hovered)
        self._draw_footer()

    def run(self) -> None:
        """Open a paused window; close it with Escape or the window's X."""
        try:
            self._setup()
            clock = pygame.time.Clock()
            while self._events():
                # Aim for 60 frames/second; tick returns milliseconds, so
                # divide by 1000 for seconds. Cap a frame at 0.1 seconds to
                # avoid a large playback jump after dragging or losing focus.
                self._update(min(clock.tick(60) / 1000, 0.1))
                self._draw()
                # Present the completed frame after all drawing is finished.
                pygame.display.flip()
        except pygame.error as error:
            # Translate graphics failures into the error main already handles.
            message = f"Could not open the Pygame view: {error}"
            raise RuntimeError(message) from error
        finally:
            # Release the display even after an error or early exit.
            pygame.quit()
