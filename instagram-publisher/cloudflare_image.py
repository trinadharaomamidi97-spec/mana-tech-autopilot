#!/usr/bin/env python3
"""Generate a clean photo-style Instagram image with Cloudflare Workers AI.

This module generates standalone AI image previews and is not connected to
legacy Wikimedia image sourcing or publishing state.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import uuid
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

MODEL = "@cf/black-forest-labs/flux-2-klein-9b"
API_ROOT = "https://api.cloudflare.com/client/v4/accounts"
MAX_RESPONSE_BYTES = 30 * 1024 * 1024

DEFAULT_PROMPT = (
    "Create a breathtaking, colourful, photorealistic underwater scene featuring "
    "a graceful bioluminescent jellyfish drifting through a vibrant deep-sea world. "
    "Show luminous blue, violet and turquoise light, delicate transparent textures, "
    "tiny glowing marine organisms and rich natural depth. Cinematic wildlife "
    "photography, crisp detail, immersive composition. Vertical 9:16. Absolutely "
    "no text, letters, captions, logos, watermarks, borders, panels, boxes, "
    "poster design, infographic, or graphic overlays."
)


def cloudflare_generate(prompt: str, account_id: str, token: str) -> bytes:
    boundary = "----ManaTech" + uuid.uuid4().hex
    fields = {
        "prompt": prompt,
        "width": "1080",
        "height": "1920",
    }
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            value.encode("utf-8"),
            b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)

    url = f"{API_ROOT}/{account_id}/ai/run/{MODEL}"
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "ManaTechTelugu-AI-Image-Test/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=240) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        detail = exc.read(4000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare API returned HTTP {exc.code}: {detail}") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not reach Cloudflare Workers AI: {exc}") from None

    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Cloudflare response exceeded the 30 MB safety limit.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("Cloudflare returned a non-JSON response.") from None

    if not payload.get("success"):
        errors = payload.get("errors") or []
        raise RuntimeError("Cloudflare image generation failed: " + json.dumps(errors)[:3000])

    encoded = (payload.get("result") or {}).get("image")
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeError("Cloudflare response did not contain result.image.")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception:
        raise RuntimeError("Cloudflare returned invalid Base64 image data.") from None
    if len(image_bytes) < 10_000:
        raise RuntimeError("Generated image is unexpectedly small.")
    return image_bytes


def save_variants(image_bytes: bytes, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(BytesIO(image_bytes)) as original:
            original = ImageOps.exif_transpose(original).convert("RGB")
            if original.width < 700 or original.height < 1000:
                raise RuntimeError(
                    f"Generated image resolution is too small: {original.width}x{original.height}"
                )

            # Story is the full vertical master. Feed is a centered 4:5 crop.
            story = ImageOps.fit(
                original, (1080, 1920), method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            feed = ImageOps.fit(
                original, (1080, 1350), method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.48),
            )
            story_path = output_dir / "story-9x16.jpg"
            feed_path = output_dir / "feed-4x5.jpg"
            story.save(story_path, "JPEG", quality=94, optimize=True, progressive=True)
            feed.save(feed_path, "JPEG", quality=94, optimize=True, progressive=True)

            for path, expected in ((story_path, (1080, 1920)), (feed_path, (1080, 1350))):
                if path.stat().st_size > 8 * 1024 * 1024:
                    raise RuntimeError(f"{path.name} exceeds Instagram's 8 MB image limit.")
                with Image.open(path) as check:
                    if check.size != expected:
                        raise RuntimeError(f"Unexpected dimensions for {path.name}: {check.size}")
                    check.verify()
                print(f"Created {path} ({path.stat().st_size:,} bytes; {expected[0]}x{expected[1]})")
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"Cloudflare output could not be decoded as an image: {exc}") from None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output-dir", default="cloudflare-preview")
    args = parser.parse_args()

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not account_id or not token:
        raise RuntimeError(
            "Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN GitHub Actions secret."
        )
    if len(args.prompt.strip()) < 20:
        raise RuntimeError("Prompt must contain at least 20 characters.")

    print(f"Image model: {MODEL}")
    print("Generating one vertical master image with Cloudflare Workers AI...")
    image_bytes = cloudflare_generate(args.prompt.strip(), account_id, token)
    save_variants(image_bytes, Path(args.output_dir))
    print("Generation test completed. No Instagram post or story was published.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Cloudflare image test stopped safely: {exc}", file=sys.stderr)
        raise SystemExit(1)
