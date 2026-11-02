"""threejs-scene-gen - generate Three.js scenes from a text prompt.

Two modes:
  oneshot  one model call, one HTML file, no verification
  repair   generate -> render -> model reviews the render -> patch -> repeat
"""

__version__ = "0.2.0"
