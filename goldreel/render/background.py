"""Signature procedural gold geometric background renderer.

Strictly follows docs/DESIGN.md Section 2:
- Thin gold geometric lines on charcoal, meeting at angles.
- 4 to 7 strokes of 2 to 6 px, opacity 25 to 45%, blurred copy underneath.
- Slow drift (10 to 20 px over video) and gentle glow pulse (4 to 6 s cycle).
- Cached per resolution; behind a 55% black vignette for readability.
"""

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from goldreel.design.tokens import Colors


class ProceduralBackground:
    """Pre-generates and renders animated gold geometric background frames."""

    def __init__(self, width: int = 1920, height: int = 1080, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self._generate_layers()

    def _generate_layers(self) -> None:
        """Generate static base strokes, blurred glow, and vignette layers with padding for drift."""
        pad = 40  # Extra margin for drift without showing edges
        w_pad = self.width + pad * 2
        h_pad = self.height + pad * 2

        self.pad = pad
        rnd = random.Random(self.seed)

        # 1. Base charcoal background
        bg_rgb = Colors.rgb_bg
        self.base_surface = Image.new("RGBA", (w_pad, h_pad), (bg_rgb.r, bg_rgb.g, bg_rgb.b, 255))

        # 2. Generate 5-7 diagonal strokes
        num_strokes = rnd.randint(5, 7)
        strokes = []
        for _ in range(num_strokes):
            x1 = rnd.randint(0, w_pad)
            y1 = rnd.randint(0, h_pad // 2)
            x2 = rnd.randint(0, w_pad)
            y2 = rnd.randint(h_pad // 2, h_pad)
            width = rnd.randint(2, 6)
            alpha = rnd.randint(65, 115)  # 25% to 45% of 255
            strokes.append((x1, y1, x2, y2, width, alpha))

        # 3. Glow layer (blurred)
        glow_layer = Image.new("RGBA", (w_pad, h_pad), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        gold_rgb = Colors.rgb_gold
        for x1, y1, x2, y2, width, alpha in strokes:
            glow_draw.line(
                [x1, y1, x2, y2],
                fill=(gold_rgb.r, gold_rgb.g, gold_rgb.b, int(alpha * 0.7)),
                width=width + 16,
            )
        self.glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(18))

        # 4. Sharp lines layer
        self.line_layer = Image.new("RGBA", (w_pad, h_pad), (0, 0, 0, 0))
        line_draw = ImageDraw.Draw(self.line_layer)
        for x1, y1, x2, y2, width, alpha in strokes:
            line_draw.line(
                [x1, y1, x2, y2],
                fill=(gold_rgb.r, gold_rgb.g, gold_rgb.b, alpha),
                width=width,
            )

        # 5. Pre-rendered base composite
        self.static_canvas = Image.alpha_composite(self.base_surface, self.glow_layer)
        self.static_canvas = Image.alpha_composite(self.static_canvas, self.line_layer)

        # 6. Vignette overlay (55% black = ~140 alpha)
        self.vignette = Image.new("RGBA", (self.width, self.height), (10, 10, 10, 140))

    def render(self, t: float, total_duration: float = 60.0) -> Image.Image:
        """Render a background frame at timestamp t with slow drift and glow pulse."""
        dur = max(total_duration, 1.0)
        norm_t = min(1.0, max(0.0, t / dur))

        # Drift: move diagonally by up to 18 px
        drift_x = int(18.0 * norm_t)
        drift_y = int(12.0 * norm_t)

        crop_box = (
            self.pad - drift_x,
            self.pad - drift_y,
            self.pad - drift_x + self.width,
            self.pad - drift_y + self.height,
        )
        cropped = self.static_canvas.crop(crop_box)

        # Pulse: 5-second gentle cycle
        cycle = 5.0
        pulse = 0.85 + 0.15 * math.sin(2.0 * math.pi * (t % cycle) / cycle)

        # Blend vignette
        vignette_alpha = int(140 * pulse)
        vignette = Image.new("RGBA", (self.width, self.height), (10, 10, 10, vignette_alpha))
        composited = Image.alpha_composite(cropped, vignette)
        return composited.convert("RGB")
