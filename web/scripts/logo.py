## Usage:
# uv run --with requests logo.py xx.com --format png --out xx.png


import argparse
from collections import deque
from pathlib import Path

import requests
from PIL import Image


LOGO_DEV_PUBLIC_KEY = "pk_QlVkmV0RT5KxKY5CFcDJDg"


def get_company_logo(domain: str, *, fmt: str = "png") -> bytes:
    # logo.dev does not support SVG output. Formats are raster.
    url = f"https://img.logo.dev/{domain}?token={LOGO_DEV_PUBLIC_KEY}&format={fmt}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def _is_near_white(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    if a == 0:
        return False

    brightest = max(r, g, b)
    darkest = min(r, g, b)
    return brightest >= 245 and darkest >= 232 and (brightest - darkest) <= 18


def remove_border_white_background(content: bytes, *, fmt: str) -> bytes:
    if fmt != "png":
        return content

    from io import BytesIO

    with Image.open(BytesIO(content)) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        pixels = rgba.load()

        queue: deque[tuple[int, int]] = deque()
        seen: set[tuple[int, int]] = set()

        def enqueue(x: int, y: int) -> None:
            point = (x, y)
            if point in seen:
                return
            seen.add(point)
            queue.append(point)

        for x in range(width):
            enqueue(x, 0)
            enqueue(x, height - 1)
        for y in range(height):
            enqueue(0, y)
            enqueue(width - 1, y)

        while queue:
            x, y = queue.popleft()
            pixel = pixels[x, y]

            if not _is_near_white(pixel):
                continue

            pixels[x, y] = (pixel[0], pixel[1], pixel[2], 0)

            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < width and 0 <= ny < height:
                    enqueue(nx, ny)

        output = BytesIO()
        rgba.save(output, format="PNG")
        return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a company logo from logo.dev")
    parser.add_argument("domain", help="Company domain, e.g. example.com")
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg", "webp"],
        help="Output format to request from logo.dev (SVG not supported)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output file path (defaults to ./logo.<format>)",
    )
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else Path(f"logo.{args.format}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    content = get_company_logo(args.domain, fmt=args.format)
    content = remove_border_white_background(content, fmt=args.format)
    out_path.write_bytes(content)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
