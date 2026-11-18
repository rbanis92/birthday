"""Draw each photo's crop windows on the source, so framing can be judged."""
import importlib.util
import pathlib

from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location(
    "pp", "C:/www/birthday/tools/prepare_photos.py")
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

SRC = pathlib.Path("C:/www/birthday/photos")
OUT = pathlib.Path("C:/www/birthday/.shots/framing.jpg")


def crop_box(w, h, aspect, cx, cy):
    """Reproduces Pillow's ImageOps.fit crop rectangle."""
    if w / h > aspect:                      # source wider -> crop the sides
        nw = h * aspect
        x1 = (w - nw) * cx
        return x1, 0, x1 + nw, h
    nh = w / aspect                         # source taller -> crop top/bottom
    y1 = (h - nh) * cy
    return 0, y1, w, y1 + nh


files = pp.find_sources()
CW, CH = 250, 300
cols = 4
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * CW, rows * (CH + 26)), (18, 18, 18))
d = ImageDraw.Draw(sheet)
report = []

for i, p in enumerate(files):
    with Image.open(p) as im:
        im = im.convert("RGB")
        w, h = im.size
        thumb = im.copy()
        thumb.thumbnail((CW, CH), Image.LANCZOS)
        tw, th = thumb.size
        x0 = (i % cols) * CW
        y0 = (i // cols) * (CH + 26)
        sheet.paste(thumb, (x0 + (CW - tw) // 2, y0))
        td = ImageDraw.Draw(sheet)

        fx, fy = pp.FOCUS.get(p.name, pp.DEFAULT_FOCUS)
        sx, sy = tw / w, th / h
        row = [f"{i+1}. {p.name[4:16]}  focus=({fx:.2f},{fy:.2f})"]

        for name, colour in (("panel", (255, 80, 80)), ("band", (80, 220, 120))):
            vw, vh = pp.VARIANTS[name][0], pp.VARIANTS[name][1]
            bx1, by1, bx2, by2 = crop_box(w, h, vw / vh, fx, fy)
            px = x0 + (CW - tw) // 2
            py = y0
            td.rectangle([px + bx1 * sx, py + by1 * sy,
                          px + bx2 * sx, py + by2 * sy],
                         outline=colour, width=2)
            row.append(f"{name} {by1/h*100:4.1f}-{by2/h*100:4.1f}%")
        report.append("  ".join(row))
        d.text((x0 + 3, y0 + CH + 4), row[0][:40], fill=(235, 235, 235))
        d.text((x0 + 3, y0 + CH + 15), "  ".join(row[1:]), fill=(200, 200, 200))

sheet.save(OUT, quality=90)
print("\n".join(report))
print("\nwrote", OUT)
