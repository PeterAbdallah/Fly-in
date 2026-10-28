"""A basic Pygame view with zone circles, connections, and drone icons."""

import os

from src.models.drone import Drone
from src.solving.simulation import Simulation

# Keep Pygame's greeting out of the terminal movement log.
if "PYGAME_HIDE_SUPPORT_PROMPT" not in os.environ:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame


class PygameVisualizer:
    """Draw current drone positions and advance one turn per second."""

    def __init__(self, simulation: Simulation) -> None:
        """Save the simulation and fit its coordinates into a fixed window."""
        self.simulation = simulation
        self.width, self.height = 1000, 650
        self.paused = True
        self.screen: pygame.Surface
        self.font: pygame.font.Font
        # Remember where each drone started its latest half-second glide.
        self.previous: dict[int, tuple[int, int]] = {}
        self.animation_start = 0

        # Map coordinates are small and may be negative. Find their range,
        # then scale and center them so every zone fits inside the window.
        zones = list(simulation.map.graph.zones.values())
        min_x, max_x = min(z.x for z in zones), max(z.x for z in zones)
        min_y, max_y = min(z.y for z in zones), max(z.y for z in zones)
        scale = min(880 / max(1, max_x - min_x),
                    430 / max(1, max_y - min_y))
        center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2

        # Pygame Y points down, so subtract map Y to make it point upward.
        # max(1, ...) above prevents division by zero on straight-line maps.
        self.positions: dict[str, tuple[int, int]] = {
            z.name: (int(500 + (z.x - center_x) * scale),
                     int(350 - (z.y - center_y) * scale))
            for z in zones
        }

    def _drone_point(self, drone: Drone) -> tuple[int, int]:
        """Return the zone or link-midpoint pixels for this turn."""
        if drone.current_zone is not None:
            return self.positions[drone.current_zone.name]
        link = drone.current_connection
        if link is not None:
            a = self.positions[link.zone_a.name]
            b = self.positions[link.zone_b.name]
            return ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
        return self.positions[self.simulation.start.name]

    def _step(self) -> None:
        """Advance the real simulation once and print its movement line."""
        if self.simulation.turn >= self.simulation.total_turns:
            return
        # Save positions before stepping; being at the end means delivered.
        self.previous = {d.drone_id: self._drone_point(d)
                         for d in self.simulation.drones
                         if d.current_zone is not self.simulation.end}
        movements = self.simulation.step()
        if movements is not None:
            self.animation_start = pygame.time.get_ticks()
            print(movements, flush=True)
        if self.simulation.turn >= self.simulation.total_turns:
            self.paused = True

    def _draw_drone(self, point: tuple[int, int]) -> None:
        """Draw a small quadcopter using four rotors and a central body."""
        x, y = point
        # Four arms connect the body to outlined rotors, about 38 pixels wide.
        for dx, dy in ((-12, -10), (12, -10), (-12, 10), (12, 10)):
            rotor = (x + dx, y + dy)
            pygame.draw.line(self.screen, "gray", point, rotor, 4)
            pygame.draw.circle(self.screen, (30, 35, 45), rotor, 7)
            pygame.draw.circle(self.screen, "lightgray", rotor, 7, 2)
            pygame.draw.line(self.screen, "white",
                             (rotor[0] - 4, rotor[1]),
                             (rotor[0] + 4, rotor[1]), 1)
        # Draw the body last so it covers the arm joints; blue marks its front.
        body = pygame.Rect(x - 6, y - 9, 12, 18)
        pygame.draw.rect(self.screen, "gold", body, border_radius=3)
        pygame.draw.rect(self.screen, "white", body, 1, border_radius=3)
        pygame.draw.rect(self.screen, "steelblue", (x - 3, y - 5, 6, 5))

    def _draw(self) -> None:
        """Clear the old frame and draw connections, zones, and drones."""
        self.screen.fill("black")
        graph = self.simulation.map.graph

        # Draw lines first so zone circles cover the ends of each line.
        for link in graph.connections:
            pygame.draw.line(self.screen, "gray",
                             self.positions[link.zone_a.name],
                             self.positions[link.zone_b.name], 2)

        for zone in graph.zones.values():
            point = self.positions[zone.name]
            # Use map colors, with a fallback for words Pygame does not know.
            try:
                color = pygame.Color(zone.color or "gray")
            except ValueError:
                color = pygame.Color("gray")
            pygame.draw.circle(self.screen, color, point, 16)

            # Large maps show only endpoint names to limit overlapping text.
            if len(graph.zones) <= 15 or zone in (
                self.simulation.start, self.simulation.end
            ):
                label = self.font.render(zone.name, True, "white")
                rect = label.get_rect(midtop=(point[0], point[1] + 20))
                rect.clamp_ip(self.screen.get_rect())
                self.screen.blit(label, rect)

        # Drones sharing a position use one icon with their count beside it.
        # Progress goes from 0 (old position) to 1 (new position) over 500 ms.
        elapsed = pygame.time.get_ticks() - self.animation_start
        progress = min(1.0, elapsed / 500)
        counts: dict[tuple[int, int], int] = {}
        for drone in self.simulation.drones:
            if drone.current_zone is self.simulation.end:
                # Let the last landing finish before hiding a delivered drone.
                if progress == 1 or drone.drone_id not in self.previous:
                    continue
            point = self._drone_point(drone)
            old = self.previous.get(drone.drone_id, point)
            # Linear interpolation changes only the drawing, not the route.
            point = (round(old[0] + (point[0] - old[0]) * progress),
                     round(old[1] + (point[1] - old[1]) * progress))
            counts[point] = counts.get(point, 0) + 1
        for point, count in counts.items():
            self._draw_drone(point)
            if count > 1:
                label = self.font.render(str(count), True, "yellow")
                # Keep the count outside the larger rotor outlines.
                self.screen.blit(label, (point[0] + 22, point[1] - 24))

        # Show the turn and delivery counts in one text header.
        delivered = sum(d.current_zone is self.simulation.end
                        for d in self.simulation.drones)
        status = "Paused" if self.paused else "Playing"
        if self.simulation.turn == self.simulation.total_turns:
            status = "Finished"
        text = (f"Turn {self.simulation.turn}/{self.simulation.total_turns}"
                f"   Delivered {delivered}/{len(self.simulation.drones)}"
                f"   {status}")
        self.screen.blit(self.font.render(text, True, "white"), (20, 20))
        help_text = "Space: play/pause   Right arrow: next turn   Esc/X: close"
        self.screen.blit(self.font.render(help_text, True, "white"), (20, 55))

    def run(self) -> None:
        """Open a paused window and handle its event/drawing loop."""
        if any(d.path is None for d in self.simulation.drones):
            raise ValueError("Call simulator.plan() before opening the view.")
        try:
            # Only display and fonts are needed; no sound devices are started.
            pygame.display.init()
            pygame.font.init()
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Fly-in")
            self.font = pygame.font.Font(None, 24)
            clock = pygame.time.Clock()
            self.paused = True
            self.previous.clear()

            # Pygame sends this event every 1000 ms, independently of frames.
            pygame.time.set_timer(pygame.USEREVENT, 1000)
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_SPACE:
                            if (
                                self.simulation.turn
                                < self.simulation.total_turns
                            ):
                                self.paused = not self.paused
                        elif event.key == pygame.K_RIGHT:
                            self.paused = True
                            self._step()
                    elif event.type == pygame.USEREVENT and not self.paused:
                        self._step()

                self._draw()
                pygame.display.flip()
                # Draw 30 frames/second; advance simulation once a second.
                clock.tick(30)
        finally:
            # Closing the window also stops the timer and releases resources.
            pygame.quit()
