import pygame
import math

from .sim import Cylinder


def kelvin_to_rgb(temp_k: float) -> tuple[int, int, int]:
    """
    Convert a color temperature in Kelvin to an approximate RGB color.
    Returns (R, G, B) values from 0–255.
    """

    # Clamp to valid range for this approximation
    temp_k = max(1000.0, min(temp_k, 40000)) / 100.0

    # Red
    if temp_k <= 66:
        red = 255
    else:
        red = temp_k - 60
        red = 329.698727446 * (red ** -0.1332047592)
        red = max(0, min(255, red))

    # Green
    if temp_k <= 66:
        green = 99.4708025861 * math.log(temp_k) - 161.1195681661
    else:
        green = temp_k - 60
        green = 288.1221695283 * (green ** -0.0755148492)
    green = max(0, min(255, green))

    # Blue
    if temp_k >= 66:
        blue = 255
    elif temp_k <= 19:
        blue = 0
    else:
        blue = 138.5177312231 * math.log(temp_k - 10) - 305.0447927307
        blue = max(0, min(255, blue))

    return int(red), int(green), int(blue)


class View:
    def __init__(self, surface, cylinder: Cylinder, debug: bool = False):
        self.surface = surface
        self.debug_layer = None
        self.cylinder = cylinder
        self.debug = debug

        if self.debug:
            self.debug_layer = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
            self.font = pygame.sysfont.SysFont("monospace", 16)

        self.view_x = self.surface.get_width() // 2
        self.view_y = self.surface.get_height() // 2
        self.scale = 5  # Please dont change this. Rendering is fucked
        self.down_offset = 200

        self.crank_view = self.__generate_crank_surface()

    def __generate_crank_surface(self):
        surface = pygame.Surface(((self.cylinder.crank_radius * 1000) * self.scale * 2 + (10 * self.scale),
                                  (self.cylinder.crank_radius * 1000) * self.scale * 2 + (10 * self.scale)),
                                 pygame.SRCALPHA)

        third_width = (self.cylinder.crank_radius * 1000) * self.scale * (2 / 3)
        sixth_width = int(third_width // 2)

        pygame.draw.rect(
            surface,
            (150, 150, 150),
            (third_width + (5 * self.scale), 0, third_width, third_width * 2 + (5 * self.scale)),
            border_radius=sixth_width,
        )

        pygame.draw.circle(
            surface,
            (50, 50, 50),
            (third_width + sixth_width + (5 * self.scale), sixth_width),
            sixth_width * 0.6,
        )

        return surface

    def render_crank(self):
        angle_degrees = -math.degrees(self.cylinder.crank_rotation)
        rotated_image = pygame.transform.rotate(self.crank_view, angle_degrees)

        original_center_x = self.view_x - (self.cylinder.crank_radius * 1000) * self.scale + (
                    (self.cylinder.crank_radius * 1000) * self.scale)  # Something isn't right!
        original_center_y = self.view_y + (self.cylinder.crank_radius * 1000) * self.scale + (
                    (self.cylinder.crank_radius * 1000) * self.scale) + 50  # bodge constant

        rotated_rect = rotated_image.get_rect(center=(original_center_x, original_center_y))
        self.surface.blit(rotated_image, rotated_rect.topleft)

        if self.debug:
            dx, dy = self.cylinder.crank_position
            pygame.draw.line(
                self.debug_layer,
                (0, 0, 255),
                (self.view_x, self.view_y + self.down_offset),
                (self.view_x + (dx * 1000) * self.scale, self.view_y + self.down_offset - (dy * 1000) * self.scale),
                width=3,
            )

            pygame.draw.circle(
                self.debug_layer,
                (255, 0, 0),
                (self.view_x, self.view_y + self.down_offset),
                (self.cylinder.crank_radius * 1000) * self.scale,
                width=self.scale // 2
            )

            pygame.draw.circle(
                self.debug_layer,
                (255, 0, 0),
                (self.view_x, self.view_y + self.down_offset),
                2,
            )

    def render_piston_shaft(self):
        dx, dy = self.cylinder.crank_position

        pygame.draw.line(
            self.surface,
            (140, 140, 140),
            (self.view_x, self.view_y + self.down_offset - ((self.cylinder.pin_offset * 1000) * self.scale)),
            (self.view_x + (dx * 1000) * self.scale, self.view_y + self.down_offset - (dy * 1000) * self.scale),
            width=int((self.cylinder.crank_radius * 1000) * self.scale * (2 / 6))
        )

        if self.debug:
            pygame.draw.line(
                self.debug_layer,
                (0, 0, 255),
                (self.view_x, self.view_y + self.down_offset - ((self.cylinder.pin_offset * 1000) * self.scale)),
                (self.view_x + (dx * 1000) * self.scale, self.view_y + self.down_offset - (dy * 1000) * self.scale),
                width=3,
            )

            pygame.draw.line(
                self.debug_layer,
                (255, 255, 0),
                (self.view_x, self.view_y + self.down_offset - ((self.cylinder.pin_offset * 1000) * self.scale)),
                (self.view_x, self.view_y + self.down_offset),
                width=1,
            )

    def render_piston_head(self):
        center_x, center_y = self.view_x, self.view_y + self.down_offset - (
                    (self.cylinder.pin_offset * 1000) * self.scale)

        pygame.draw.rect(
            self.surface,
            (150, 150, 150),
            (center_x - (self.cylinder.radius * 1000) + 1, center_y, (self.cylinder.radius * 1000) * 2, 50),
            border_radius=5
        )

        if self.debug:
            pygame.draw.line(
                self.debug_layer,
                (255, 0, 0),
                (center_x - (self.cylinder.radius * 1000), center_y),
                (center_x + (self.cylinder.radius * 1000), center_y)
            )

    def render_cylinder(self):
        center_x, center_y = self.view_x, self.view_y + self.down_offset - ((self.cylinder.height * 1000) * self.scale)

        pygame.draw.line(
            self.surface,
            (160, 160, 160),
            (center_x + (self.cylinder.radius * 1000) + 2, center_y),
            (center_x + (self.cylinder.radius * 1000) + 2, center_y + ((self.cylinder.radius * 1000) * 2)),
            width=4
        )

        pygame.draw.line(
            self.surface,
            (160, 160, 160),
            (center_x - (self.cylinder.radius * 1000) - 2, center_y),
            (center_x - (self.cylinder.radius * 1000) - 2, center_y + ((self.cylinder.radius * 1000) * 2)),
            width=4
        )

        pygame.draw.line(
            self.surface,
            (160, 160, 160),
            (center_x - (self.cylinder.radius * 1000) - 2, center_y),
            (center_x + (self.cylinder.radius * 1000) + 2, center_y),
            width=4
        )

        colour = kelvin_to_rgb(self.cylinder.temperature)

        pygame.draw.rect(
            self.surface,
            colour,
            (center_x - (self.cylinder.radius * 1000) + 1, center_y + 2,
             (self.cylinder.radius * 1000) * 2, ((self.cylinder.height - self.cylinder.pin_offset) * 1000 * self.scale))
        )

        if self.debug:
            rect = self.font.render(f"{round(self.cylinder.temperature - 273)}°C", True, (255, 255, 255))
            self.debug_layer.blit(
                rect, (center_x - rect.get_width() // 2, center_y + 10)
            )

    def draw(self):
        self.surface.fill((0, 0, 0))

        if self.debug:
            self.debug_layer.fill((0, 0, 0, 0))

        self.render_piston_shaft()
        self.render_crank()
        self.render_piston_head()
        self.render_cylinder()

        if self.debug:
            text = self.font.render(f"Stats", True, (255, 255, 255))
            self.debug_layer.blit(text, (5, 5))

            text = self.font.render(f"RPM: {round(self.cylinder.rpm)}", True, (255, 255, 255))
            self.debug_layer.blit(text, (5, 20))

            text = self.font.render(f"Mode: {self.cylinder.mode}", True, (255, 255, 255))
            self.debug_layer.blit(text, (5, 35))

            self.surface.blit(self.debug_layer, (0, 0))
