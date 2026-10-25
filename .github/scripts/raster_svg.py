"""Build-time SVG rasterization; no browser-side filters needed for settled art."""
import base64
import subprocess


def png_data(svg, width, height):
    try:
        result = subprocess.run(
            ["rsvg-convert", "--width", str(width), "--height", str(height)],
            input=svg.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Install librsvg2-bin (rsvg-convert) to generate panels") from error
    return "data:image/png;base64," + base64.b64encode(result.stdout).decode("ascii")
