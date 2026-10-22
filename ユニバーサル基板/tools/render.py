"""Dependency-free SVG drawings with physical-mm scale and mirrored bottom view."""
from __future__ import annotations

import html
import math
from pathlib import Path

from model import EPS, column, hole, rect_intersects
from router import net_colour


def esc(value):
    return html.escape(str(value), quote=True)


def drawing(p, view="top", scale=1, annotate=False):
    mirrored = view == "bottom"
    margin = 16.0
    board_w, board_h = p.board_rect[2] - p.board_rect[0], p.board_rect[3] - p.board_rect[1]
    grid_x, grid_y = -p.board_rect[0], -p.board_rect[1]
    side_x = margin + board_w + 7
    canvas_w = max(170, side_x + 59)
    legend_rows = len(p.nets) + 7
    values_y = max(margin + board_h + 17, legend_rows * 2.6 + 12)
    parts = sorted(p.parts.values(), key=lambda z: z.id)
    canvas_h = max(values_y + math.ceil(len(parts) / 3) * 2.3 + 1, margin + board_h + 18)
    objects = []

    def xy(q):
        x, y = q
        return margin + board_w - grid_x - x * p.pitch if mirrored else margin + grid_x + x * p.pitch, margin + grid_y + y * p.pitch

    def rect_mm(rect):
        x0, y0, x1, y1 = rect
        left = margin + board_w - grid_x - x1 if mirrored else margin + grid_x + x0
        return left, margin + grid_y + y0, x1 - x0, y1 - y0

    def text(x, y, value, size=1.8, anchor="start", fill="#202a35", **kwargs):
        attributes = " ".join(f'{k.replace("_", "-")}="{esc(v)}"' for k, v in kwargs.items())
        objects.append(f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" {attributes}>{esc(value)}</text>')

    def line(a, b, colour, width=0.3, dashed=False):
        objects.append(f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" x2="{b[0]:.3f}" y2="{b[1]:.3f}" stroke="{colour}" stroke-width="{width}"' + (' stroke-dasharray="1.1,0.65"' if dashed else '') + '/>')

    title = "BOTTOM VIEW (mirrored)" if mirrored else "TOP VIEW" if view == "top" else "OVERLAY (TOP coordinates)"
    text(margin, 5.5, title, 3.2, font_weight="bold")
    text(margin, 9, f"{p.columns} x {p.rows} holes | pitch 2.54 mm | print {scale}:1 | coords always TOP view", 1.8)
    provisional = p.board.get("provisional", False) or any(q.footprint.get("provisional") for q in parts)
    text(side_x, 5.5, "PROVISIONAL / NOT FOR BUILD" if provisional else "DIMENSIONS REQUIRE FIT CHECK", 2, fill="#b72b24", font_weight="bold")
    objects.append(f'<rect x="{margin}" y="{margin}" width="{board_w}" height="{board_h}" fill="#fffdf5" stroke="#64748b" stroke-width="0.3"/>')
    if p.has_outline:
        # Physical mounting holes are shown as drawing metadata. Their actual
        # hardware clearance still comes from explicit keepouts / T7 checks.
        for mount in p.board.get("mounting_holes_mm", []):
            x = margin + (board_w - mount["x"] if mirrored else mount["x"])
            y = margin + mount["y"]
            objects.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{mount["diameter"] / 2:.3f}" fill="#dce1e7" stroke="#64748b" stroke-width="0.2"><title>{esc(mount.get("id", "mount"))} physical mounting hole (hardware clearance separately checked)</title></circle>')
    for a, b, name in p.keepouts:
        coords = rect_mm(((a[0] - 0.5) * p.pitch, (a[1] - 0.5) * p.pitch, (b[0] + 0.5) * p.pitch, (b[1] + 0.5) * p.pitch))
        objects.append(f'<rect x="{coords[0]:.3f}" y="{coords[1]:.3f}" width="{coords[2]:.3f}" height="{coords[3]:.3f}" fill="url(#hatch)" stroke="#c2410c" stroke-width="0.25"><title>{esc(name)}</title></rect>')
    for x in range(p.columns):
        a, b = xy((x, 0)), xy((x, p.rows - 1))
        line(a, b, "#e0e2e5", 0.08)
        text(a[0], margin - 1.7, column(x), 1.65, "middle")
        text(a[0], margin + board_h + 2.6, column(x), 1.65, "middle")
    for y in range(p.rows):
        a, b = xy((0, y)), xy((p.columns - 1, y))
        line(a, b, "#e0e2e5", 0.08)
        text(margin - 1.6, a[1] + 0.55, y + 1, 1.65, "end")
        text(margin + board_w + 1.6, a[1] + 0.55, y + 1, 1.65)
        for x in range(p.columns):
            px, py = xy((x, y))
            objects.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="0.32" fill="#fff" stroke="#c7bda9" stroke-width="0.12"/>')
    if view in ("top", "overlay"):
        for part in parts:
            x, y, w, h = rect_mm(part.rect)
            fill = "#f7d8c7" if part.footprint["hot"] else "#e3edf6" if len(part.pins) >= 5 else "#e9efd9"
            objects.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" rx="0.35" fill="{fill}" fill-opacity="0.88" stroke="#536270" stroke-width="0.25"><title>{esc(part.id)} — {esc(part.data.get("value", ""))}</title></rect>')
    for c in p.conductors:
        exposed = c["kind"] != "jumper"
        visible = view == "overlay" or (mirrored and (exposed or c["side"] == "bottom")) or (view == "top" and not exposed and c["side"] == "top")
        if not visible:
            continue
        coordinates = [xy(q) for q in c["xy"]]
        path = " ".join(f"{x:.3f},{y:.3f}" for x, y in coordinates)
        colour = net_colour(c["net"])
        width = 0.65 if c["net"] in ("VM", "GND") else 0.42
        style = ' stroke-dasharray="1.2,0.65"' if not exposed else ''
        objects.append(f'<polyline points="{path}" fill="none" stroke="white" stroke-width="{width + 0.38}" stroke-linejoin="round" stroke-linecap="round"/>')
        objects.append(f'<polyline points="{path}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{style}><title>{esc(c["id"])} {esc(c["net"])} {esc(c["kind"])} {esc(" → ".join(c["path"]))}</title></polyline>')
        if mirrored or view == "overlay":
            for q in set(c["contacts"]):
                x, y = xy(q)
                objects.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.48" fill="{colour}" stroke="white" stroke-width="0.10"/>')
        if annotate:
            a, b = coordinates[0], coordinates[1]
            text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 0.5, c["id"], 1.25, "middle", colour, stroke="white", stroke_width="0.4", paint_order="stroke")
    for part in parts:
        for pin in part.pins:
            x, y = xy(pin.xy)
            colour = "#888888" if pin.net == "NC" else net_colour(pin.net)
            objects.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.55" fill="white" stroke="{colour}" stroke-width="0.28"><title>{esc(pin.label)} #{esc(pin.number)} {esc(pin.net)} {hole(pin.xy)}</title></circle>')
            mapped = part.data.get("pin_map", {})
            orig_number = next((n for n, d in mapped.items() if d["number"] == pin.number), pin.number)
            if orig_number == part.footprint.get("polarity", {}).get("pin", "1"):
                objects.append(f'<rect x="{x - 0.82:.3f}" y="{y - 0.82:.3f}" width="1.64" height="1.64" fill="none" stroke="#ae2424" stroke-width="0.22"/>')
    for q, label in p.reserved_pads.items():
        x, y = xy(q)
        line((x - 0.6, y - 0.6), (x + 0.6, y + 0.6), "#6b7280", 0.25)
        line((x - 0.6, y + 0.6), (x + 0.6, y - 0.6), "#6b7280", 0.25)
        objects.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.9" fill="none" stroke="#6b7280" stroke-width="0.15"><title>{esc(label)} NC reserved</title></circle>')
    # Greedy label placement with explicit text boxes. Large bodies receive their
    # labels inside; small bodies use clear nearby callouts. Values live in a key.
    boxes = []
    body_boxes = {part.id: rect_mm(part.rect) for part in parts}
    for part in sorted(parts, key=lambda q: (-len(q.pins), q.id)):
        x, y, w, h = body_boxes[part.id]
        size, textw = 1.95, max(3.2, len(part.id) * 1.2)
        candidates = []
        if w >= textw + 1 and h >= 5:
            candidates.append((x + w / 2, y + h / 2))
        for gap in (1.8, 3.8, 6, 8.2, 10.4):
            candidates.extend(((x + w / 2, y - gap), (x + w / 2, y + h + gap), (x - textw / 2 - gap, y + h / 2), (x + w + textw / 2 + gap, y + h / 2)))
        # Dense probe clusters need diagonal callouts into nearby free space.
        offsets = sorted(((dx, dy) for dx in range(-8, 9) for dy in range(-8, 9)), key=lambda q: (q[0] * q[0] + q[1] * q[1], q))
        candidates.extend((x + w / 2 + dx * 2.5, y + h / 2 + dy * 2.5) for dx, dy in offsets)
        chosen = None
        for tx, ty in candidates:
            box = (tx - textw / 2 - 0.25, ty - size + 0.1, tx + textw / 2 + 0.25, ty + 0.6)
            if box[0] < margin or box[2] > margin + board_w or box[1] < margin or box[3] > margin + board_h:
                continue
            if any(rect_intersects(box, q, 0.35) for q in boxes):
                continue
            obstacles = []
            for other in parts:
                if other.id == part.id:
                    continue
                ox, oy, ow, oh = body_boxes[other.id]
                obstacles.append((ox, oy, ox + ow, oy + oh))
            if any(rect_intersects(box, q, 0.2) for q in obstacles):
                continue
            if any(rect_intersects(box, (px - 0.75, py - 0.75, px + 0.75, py + 0.75), 0.2) for other in parts if other.id != part.id for px, py in (xy(q.xy) for q in other.pins)):
                continue
            chosen = tx, ty, box
            break
        if chosen is None:
            tx, ty = x + w / 2, y + h / 2
            chosen = tx, ty, (tx - textw / 2, ty - 2, tx + textw / 2, ty + 0.5)
        tx, ty, box = chosen
        boxes.append(box)
        if not (x <= tx <= x + w and y <= ty <= y + h):
            line((x + w / 2, y + h / 2), (tx, ty - 0.5), "#697586", 0.15)
        text(tx, ty, part.id, size, "middle", stroke="#fffdf5", stroke_width="0.6", paint_order="stroke", font_weight="bold")
    text(side_x, 14, "NET COLOURS", 2.4, font_weight="bold")
    for i, net in enumerate(p.nets):
        y = 18 + i * 2.6
        line((side_x, y - 0.5), (side_x + 5, y - 0.5), net_colour(net), 0.6)
        text(side_x + 7, y, net, 1.8)
    y = 21 + len(p.nets) * 2.6
    for label in ("Solid: bare / bridge", "Dashed: insulated jumper", "Square: pin 1 / polarity", "Filled dots: solder contacts", "NC: no wire / no solder bridge"):
        text(side_x, y, label, 1.7)
        y += 2.7
    # A calibration ruler is in actual board millimetres, hence doubles at scale 2.
    ruler_y = margin + board_h + 7
    line((margin, ruler_y), (margin + 20, ruler_y), "#111", 0.3)
    line((margin, ruler_y - 1), (margin, ruler_y + 1), "#111", 0.3)
    line((margin + 20, ruler_y - 1), (margin + 20, ruler_y + 1), "#111", 0.3)
    text(margin + 23, ruler_y + 0.6, f"20 mm calibration (printed {20 * scale:g} mm)", 1.7)
    text(margin, values_y - 2.2, "PART VALUES (refdes are placed on the drawing; full values below)", 2.2, font_weight="bold")
    colw = (canvas_w - 2 * margin) / 3
    nrows = math.ceil(len(parts) / 3)
    for i, part in enumerate(parts):
        col, row = divmod(i, nrows)
        text(margin + col * colw, values_y + row * 2.3, f"{part.id}  {part.data.get('value', '')}"[:54], 1.75)
    defs = '<defs><pattern id="hatch" width="2" height="2" patternUnits="userSpaceOnUse"><path d="M0,2 L2,0" stroke="#e5af83" stroke-width="0.2"/></pattern></defs>'
    content = defs + '<g font-family="Arial, sans-serif">' + "\n".join(objects) + '</g>'
    metadata = f'<desc>Perfboard {esc(title)}. TOP hole identity is unchanged when mirrored. Board geometry is millimetres. {"Provisional footprints, not approved for construction." if provisional else ""}</desc>'
    def svg(vb, w, h):
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="{vb}">{metadata}<rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="white"/>{content}</svg>\n'
    return svg(f"0 0 {canvas_w:.3f} {canvas_h:.3f}", canvas_w * scale, canvas_h * scale), (canvas_w, canvas_h), svg


def render(p, output, views=("top", "bottom", "overlay"), scale=1, tiles=False, annotate=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for view in views:
        content, (w, h), svg = drawing(p, view, scale, annotate)
        path = output / f"{view}.svg"
        path.write_text(content, encoding="utf-8")
        paths.append(path)
        if tiles:
            pagew, pageh = 277 / scale, 190 / scale  # A4 landscape with 10 mm printer margins.
            for row in range(math.ceil(h / pageh)):
                for col in range(math.ceil(w / pagew)):
                    path = output / f"{view}-a4-r{row + 1}c{col + 1}.svg"
                    path.write_text(svg(f"{col * pagew:.3f} {row * pageh:.3f} {pagew:.3f} {pageh:.3f}", 277, 190), encoding="utf-8")
                    paths.append(path)
    return paths
