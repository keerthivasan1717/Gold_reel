"""Motion easing functions for GoldReel render engine.

Strictly follows docs/DESIGN.md Section 6:
"Easing: ease-in-out-quad for movement, ease-out-quad for entrances. No bounce."
"""


def clamp01(t: float) -> float:
    """Clamp value between 0.0 and 1.0."""
    return max(0.0, min(1.0, t))


def linear(t: float) -> float:
    """Linear progression."""
    return clamp01(t)


def ease_out_quad(t: float) -> float:
    """Ease out quad: fast start, decelerating to a stop.

    Ideal for UI card and bar entrances.
    Formula: 1 - (1 - t)^2
    """
    t = clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out_quad(t: float) -> float:
    """Ease in out quad: acceleration then deceleration.

    Ideal for continuous transitions and position swapping.
    """
    t = clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0

