#!/usr/bin/env python3
"""Turn the photos dropped in photos/ into small, fast web images.

    py -3 tools/prepare_photos.py            # build derivatives
    py -3 tools/prepare_photos.py --check    # report what is there, change nothing

Originals stay untouched in photos/. Output goes to photos/web/ as WebP, already
cropped to the exact aspect ratios the page uses, plus a 12px blurred
placeholder embedded as a data URI in manifest.json (so the page can paint
something warm before the real image arrives, with no extra request).

  panel  4:3 -> the photo at the top of the scratch card
  band   3:2 -> the strip across a reason card

Cropping is focal, not centred: FOCUS below nudges the crop window toward the
faces. Any photo not listed gets a sensible upper-third default. Re-run this
whenever a photo is added or replaced. Order is the alphabetical order of the
original filenames, so rename them (01-*.jpg, 02-*.jpg, ...) to control it.
"""

import argparse
import base64
import io
import json
import pathlib
import sys

try:
    from PIL import Image, ImageFilter, features
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required:  py -3 -m pip install Pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "photos"
OUT = SRC / "web"
SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff"}

# (name, width, height, quality) — each matches the exact aspect ratio of the
# box it lands in, so the browser never crops a second time. Widths are sized
# for a 390pt phone at DPR 3 (a ~983px box), which is as sharp as any phone can
# show; the whole set is still under 1.5 MB because these are WebP at q~78.
VARIANTS = {
    "panel": (1000, 750, 80),  # 4:3  — the scratch card's photo
    "band":  (980, 653, 78),   # 3:2  — the strip across a reason card
}
BLUR_W = 12

# focal point per source filename, as a fraction of width/height.
# x is almost always centred; y is where the faces sit.
FOCUS = {
    "IMG_20250828_130619.jpg": (0.52, 0.22),
    "IMG_20251105_105919.jpg": (0.52, 0.26),
    "IMG_20251105_110410681_HDR_AE.jpg": (0.50, 0.24),
    "IMG_20260323_124350.jpg": (0.52, 0.24),
    "IMG_20260418_200730.jpg": (0.48, 0.40),
    "IMG_20260526_200617.jpg": (0.54, 0.42),
    "IMG_20260618_114329.jpg": (0.52, 0.28),
    "IMG_20260826_153227.jpg": (0.50, 0.26),
}
DEFAULT_FOCUS = (0.50, 0.30)


def load_heif_support():
    """HEIC (iPhone photos) needs pillow-heif. Report, do not install silently."""
    try:
        import pillow_heif  # noqa: F401
        pillow_heif.register_heif_opener()
        return True
    except ImportError:
        return False


def find_sources():
    return sorted(
        p for p in SRC.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIXES
    )


def encode(im, quality):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=6)
    return buf.getvalue()


def build_one(src: pathlib.Path, index: int):
    fx, fy = FOCUS.get(src.name, DEFAULT_FOCUS)
    stem = f"{index:02d}-{src.stem.lower().replace(' ', '-')[:40]}"
    made = {}

    with Image.open(src) as im:
        im = im.convert("RGB")          # drops alpha, normalises HEIC/CMYK/16-bit
        w, h = im.size

        for name, (vw, vh, q) in VARIANTS.items():
            # ImageOps.fit does the focal crop *and* the resize in one pass
            variant = fit(im, (vw, vh), (fx, fy))
            data = encode(variant, q)
            fname = f"{stem}-{name}.webp"
            (OUT / fname).write_bytes(data)
            made[name] = {"file": fname, "w": vw, "h": vh, "bytes": len(data)}

        # a whisper of a placeholder: 12px wide, inline, ~300 bytes
        blur = fit(im, (BLUR_W, round(BLUR_W * 3 / 2)), (fx, fy))
        blur = blur.filter(ImageFilter.GaussianBlur(1.1))
        tiny = encode(blur, 40)
        made["blur"] = {
            "uri": "data:image/webp;base64," + base64.b64encode(tiny).decode("ascii"),
            "bytes": len(tiny),
        }

    return {
        "source": src.name,
        "width": w,
        "height": h,
        "portrait": h >= w,
        "focus": [fx, fy],
        "variants": made,
    }


def fit(im, size, centering):
    """Crop to `size`'s aspect around a focal point, then resize."""
    from PIL import ImageOps
    return ImageOps.fit(im, size, method=Image.LANCZOS, centering=centering)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report, do not write")
    args = ap.parse_args()

    if not SRC.is_dir():
        sys.exit(f"missing folder: {SRC}")

    sources = find_sources()
    if not sources:
        print(f"no photos yet - drop them in {SRC} and run this again")
        return 0

    heic = [p.name for p in sources if p.suffix.lower() in (".heic", ".heif")]
    have_heif = load_heif_support()
    if heic and not have_heif:
        print("HEIC photos found but pillow-heif is not installed:")
        for name in heic:
            print("  -", name)
        print("\nInstall it (one time), then re-run:")
        print("  py -3 -m pip install pillow-heif")
        return 1

    if not features.check("webp"):
        sys.exit("this Pillow build cannot write WebP")

    print(f"found {len(sources)} photo(s) in {SRC}")
    if args.check:
        for p in sources:
            with Image.open(p) as im:
                fx, fy = FOCUS.get(p.name, DEFAULT_FOCUS)
                mark = "" if p.name in FOCUS else "  (default focus)"
                print(f"  {p.name}  {im.size[0]}x{im.size[1]}  {im.mode}"
                      f"  focus=({fx:.2f},{fy:.2f}){mark}")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, src in enumerate(sources, start=1):
        try:
            entry = build_one(src, index)
        except Exception as exc:
            print(f"  ! {src.name}: {exc}")
            continue
        manifest.append(entry)
        src_mb = src.stat().st_size / 1024 / 1024
        out_kb = sum(v["bytes"] for k, v in entry["variants"].items() if k != "blur") / 1024
        print(f"  {src.name}  {src_mb:5.1f} MB -> {out_kb:6.1f} KB")
        for kind, meta in entry["variants"].items():
            if kind == "blur":
                print(f"      {kind:>5}  inline placeholder            "
                      f"{meta['bytes']/1024:6.2f} KB")
            else:
                print(f"      {kind:>5}  {meta['file']:<34}"
                      f" {meta['w']}x{meta['h']}  {meta['bytes']/1024:6.1f} KB")

    payload = json.dumps({"photos": manifest}, indent=1)

    # Two copies of the same data, on purpose:
    #   manifest.json - for humans, and for tooling
    #   photos.js     - what the page actually loads
    # A browser refuses to fetch() a local file when the page is opened by
    # double-clicking it (file://), but a plain <script src> is not subject to
    # that rule. Emitting this means the page works both from a server and
    # straight off the disk, which matters a lot on the day it is sent.
    (OUT / "manifest.json").write_text(payload, encoding="utf-8", newline="\n")
    (OUT / "photos.js").write_text(
        "/* generated by tools/prepare_photos.py - do not edit by hand */\n"
        f"window.ALO_PHOTOS = {json.dumps({'photos': manifest})};\n",
        encoding="utf-8", newline="\n")

    total = sum(f.stat().st_size for f in OUT.glob("*.webp"))
    print(f"\n{len(manifest)} photo(s), {total/1024/1024:.2f} MB of WebP in {OUT}")
    print(f"manifest: {(OUT / 'manifest.json').stat().st_size/1024:.1f} KB "
          f"(+ photos.js, the copy the page loads)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
