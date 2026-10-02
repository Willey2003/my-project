#!/usr/bin/env python3
"""Architecture-diagram generator for the lab kit.

Reads a small YAML spec and writes three files next to each other:
  <name>.drawio  uncompressed mxfile (opens in draw.io / diagrams.net; File > Export as > VSDX for Visio)
  <name>.svg     standalone SVG with the same layout
  <name>.png     rendered from the SVG with Playwright (Chromium) at device scale 2

Usage:
  python3 lab/architecture/diagram.py spec.yaml outdir/ [--name NAME] [--no-png]

<name> defaults to the spec file name without its extension. See lab/architecture/README.md
for the spec schema.

Dependencies: PyYAML (pip install pyyaml); for the PNG, Python Playwright (pip install playwright)
or Node Playwright. A Chromium already on disk is used; nothing is downloaded.
"""
from __future__ import annotations

import argparse
import glob
import heapq
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

# --------------------------------------------------------------------------------------------
# Visual constants
# --------------------------------------------------------------------------------------------
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
GRID = 10                 # routing grid and snapping step (px)
MARGIN = 40               # outer canvas margin
TITLE_H = 64              # space reserved for the title
GROUP_PAD = 20            # inner padding of a group
GROUP_HEAD = 30           # height of a group's label band
GROUP_GAP = 40            # gap between sibling groups
NODE_GAP_X = 50           # horizontal gap between nodes in a group grid
NODE_GAP_Y = 50           # vertical gap between nodes in a group grid
NODE_MIN_W = 130
NODE_MAX_W = 200
LABEL_PX = 13
SUB_PX = 12
GROUP_PX = 14
EDGE_PX = 12
CHAR_W = 0.58             # average glyph width as a fraction of the font size (system-ui)

EDGE_COLOR = "#4B5563"
TEXT_COLOR = "#1F2937"
SUBTEXT_COLOR = "#6B7280"

# role -> (tint fill, darker border, legend text)
ROLES = {
    "network":       ("#EAF1FA", "#4A78A8", "Network / ingress"),
    "compute":       ("#EDF5EC", "#5B8C5A", "Compute / workloads"),
    "data":          ("#FBF4E6", "#A8843A", "Data / storage"),
    "security":      ("#FBEEEE", "#A65656", "Security / policy"),
    "ci":            ("#F2EFF8", "#7661A3", "CI/CD / GitOps"),
    "observability": ("#E8F5F4", "#3B8683", "Observability"),
    "external":      ("#F3F4F6", "#6B7280", "External / cloud"),
    "platform":      ("#EEF1FA", "#50609F", "Platform / cluster"),
    "host":          ("#F7F6F2", "#7C7466", "Host / tooling"),
}
DEFAULT_ROLE = "external"

SHAPES = {"box", "cylinder", "cloud", "hexagon"}


def text_w(s: str, px: float) -> float:
    return len(s) * px * CHAR_W


def wrap(s: str, px: float, max_w: float) -> list[str]:
    """Greedy word wrap using the glyph-width estimate. Long words are split on - / . _ when needed."""
    words = s.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = (cur + " " + w).strip()
        if text_w(cand, px) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        while text_w(ln, px) > max_w and len(ln) > 4:
            limit = max(3, int(max_w / (px * CHAR_W)))
            cut = max((ln.rfind(c, 0, limit) for c in "-/._:"), default=-1)
            cut = cut + 1 if cut > 0 else limit
            out.append(ln[:cut])
            ln = ln[cut:]
        out.append(ln)
    return out or [""]


def snap(v: float) -> int:
    return int(math.ceil(v / GRID) * GRID)


# --------------------------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------------------------
@dataclass
class Node:
    id: str
    label: str
    sublabel: str = ""
    group: str | None = None
    shape: str = "box"
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0
    lines: list = field(default_factory=list)
    sublines: list = field(default_factory=list)

    @property
    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


@dataclass
class Group:
    id: str
    label: str
    role: str
    parent: str | None = None
    cols: int | None = None
    children: list = field(default_factory=list)   # child group ids (spec order)
    nodes: list = field(default_factory=list)      # node ids (spec order)
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0
    # layout scratch
    nw: float = 0
    nh: float = 0
    ncols: int = 0
    nrows: int = 0
    rows: list = field(default_factory=list)       # rows of child group ids
    grid_w: float = 0
    grid_h: float = 0

    @property
    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


@dataclass
class Edge:
    src: str
    dst: str
    label: str = ""
    dashed: bool = False
    points: list = field(default_factory=list)     # absolute polyline incl. endpoints
    label_pos: tuple | None = None
    label_box: tuple | None = None
    src_port: tuple | None = None                  # (fx, fy) relative to source bbox
    dst_port: tuple | None = None


class Spec:
    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise SystemExit("spec must be a YAML mapping")
        self.title = str(data.get("title", "Architecture"))
        self.subtitle = str(data.get("subtitle", "") or "")
        self.width = int(data.get("width", 1600))
        self.groups: dict[str, Group] = {}
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        for g in data.get("groups", []) or []:
            gid = str(g["id"])
            if gid in self.groups:
                raise SystemExit(f"duplicate group id {gid}")
            role = str(g.get("role", DEFAULT_ROLE))
            if role not in ROLES:
                print(f"warning: group {gid}: unknown role '{role}', using '{DEFAULT_ROLE}'", file=sys.stderr)
                role = DEFAULT_ROLE
            self.groups[gid] = Group(gid, str(g.get("label", gid)), role, g.get("parent"),
                                     int(g["cols"]) if g.get("cols") else None)
        for g in self.groups.values():
            if g.parent is not None:
                if g.parent not in self.groups:
                    raise SystemExit(f"group {g.id}: unknown parent {g.parent}")
                self.groups[g.parent].children.append(g.id)
        # cycle check
        for g in self.groups.values():
            seen, p = set(), g.parent
            while p:
                if p in seen or p == g.id:
                    raise SystemExit(f"group {g.id}: parent cycle")
                seen.add(p)
                p = self.groups[p].parent
        for n in data.get("nodes", []) or []:
            nid = str(n["id"])
            if nid in self.nodes or nid in self.groups:
                raise SystemExit(f"duplicate id {nid}")
            shape = str(n.get("shape", "box"))
            if shape not in SHAPES:
                print(f"warning: node {nid}: unknown shape '{shape}', using box", file=sys.stderr)
                shape = "box"
            grp = n.get("group")
            if grp is not None and grp not in self.groups:
                raise SystemExit(f"node {nid}: unknown group {grp}")
            self.nodes[nid] = Node(nid, str(n.get("label", nid)), str(n.get("sublabel", "") or ""), grp, shape)
            if grp:
                self.groups[grp].nodes.append(nid)
        for e in data.get("edges", []) or []:
            s, t = str(e["from"]), str(e["to"])
            for end in (s, t):
                if end not in self.nodes and end not in self.groups:
                    raise SystemExit(f"edge {s}->{t}: unknown endpoint {end}")
            self.edges.append(Edge(s, t, str(e.get("label", "") or ""), bool(e.get("dashed", False))))
        loose = [n for n in self.nodes.values() if n.group is None]
        if loose:
            # ungrouped nodes live in an implicit, borderless top-level group
            self.groups["__loose"] = Group("__loose", "", "external")
            for n in loose:
                n.group = "__loose"
                self.groups["__loose"].nodes.append(n.id)
        self.top = [g.id for g in self.groups.values() if g.parent is None]
        rows = (data.get("layout") or {}).get("rows")
        self.rows_hint = [[str(x) for x in r] for r in rows] if rows else None
        if self.rows_hint:
            flat = [x for r in self.rows_hint for x in r]
            for gid in flat:
                if gid not in self.groups or self.groups[gid].parent is not None:
                    raise SystemExit(f"layout.rows: '{gid}' is not a top-level group")
            missing = [g for g in self.top if g not in flat]
            if missing:
                self.rows_hint.append(missing)


# --------------------------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------------------------
class Layout:
    def __init__(self, spec: Spec):
        self.s = spec
        self.content_w = spec.width - 2 * MARGIN

    # ---- measuring -------------------------------------------------------------------------
    def size_nodes(self, g: Group):
        """Uniform node box for the whole group so the grid stays tidy."""
        if not g.nodes:
            g.nw = g.nh = 0
            return
        best_w = NODE_MIN_W
        for nid in g.nodes:
            n = self.s.nodes[nid]
            extra = {"cloud": 40, "hexagon": 30, "cylinder": 0, "box": 0}[n.shape]
            need = max(text_w(n.label, LABEL_PX) * 1.08, text_w(n.sublabel, SUB_PX)) + 24 + extra
            best_w = max(best_w, min(NODE_MAX_W, need))
        w = snap(best_w)
        max_lines = 1
        for nid in g.nodes:
            n = self.s.nodes[nid]
            extra = {"cloud": 40, "hexagon": 30, "cylinder": 0, "box": 0}[n.shape]
            inner = w - 20 - extra
            n.lines = wrap(n.label, LABEL_PX * 1.08, inner)
            n.sublines = wrap(n.sublabel, SUB_PX, inner) if n.sublabel else []
            max_lines = max(max_lines, len(n.lines) * 1.0 + len(n.sublines) * 0.95)
        h = 20 + max_lines * 17
        if any(self.s.nodes[i].shape == "cylinder" for i in g.nodes):
            h += 14
        if any(self.s.nodes[i].shape == "cloud" for i in g.nodes):
            h += 16
        g.nw, g.nh = w, snap(max(h, 50))

    def grid_cols(self, g: Group, max_inner: float) -> int:
        n = len(g.nodes)
        if n == 0:
            return 0
        fit = max(1, int((max_inner + NODE_GAP_X) // (g.nw + NODE_GAP_X)))
        if g.cols:
            return max(1, min(g.cols, n, fit))
        want = math.ceil(math.sqrt(n * 2.0))  # a bit wider than square
        return max(1, min(n, fit, want))

    def measure(self, gid: str, max_w: float):
        """Natural size of a group given the widest it may be. Sets g.w/g.h."""
        g = self.s.groups[gid]
        inner_max = max_w - 2 * GROUP_PAD
        self.size_nodes(g)
        g.ncols = self.grid_cols(g, inner_max)
        g.nrows = math.ceil(len(g.nodes) / g.ncols) if g.ncols else 0
        g.grid_w = g.ncols * g.nw + max(0, g.ncols - 1) * NODE_GAP_X
        g.grid_h = g.nrows * g.nh + max(0, g.nrows - 1) * NODE_GAP_Y
        for c in g.children:
            self.measure(c, inner_max)
        g.rows = self.pack(g.children, inner_max)
        # a lone group that wrapped onto its own row: try narrowing its siblings first
        if len(g.rows) > 1 and len(g.rows[-1]) == 1:
            flat = [c for r in g.rows for c in r]
            if self.shrink_row(flat, inner_max):
                g.rows = [flat]
            else:  # no luck: restore the natural sizes
                for c in flat:
                    self.measure(c, inner_max)
                g.rows = self.pack(g.children, inner_max)
        rows_w = max([self.row_w(r) for r in g.rows] or [0])
        rows_h = sum(self.row_h(r) for r in g.rows) + max(0, len(g.rows) - 1) * GROUP_GAP
        inner_w = max(g.grid_w, rows_w, text_w(g.label, GROUP_PX) * 1.15 + 10)
        inner_h = g.grid_h + (GROUP_GAP if g.grid_h and rows_h else 0) + rows_h
        head = GROUP_HEAD if g.label else 0
        g.w = snap(inner_w + 2 * GROUP_PAD)
        g.h = snap(head + inner_h + 2 * GROUP_PAD - (10 if head else 0))

    def shrink_row(self, row, max_w) -> bool:
        """Re-measure the widest multi-column groups in a row until the row fits max_w."""
        for _ in range(40):
            if self.row_w(row) <= max_w:
                return True
            cands = [c for c in row if self.s.groups[c].ncols > 1 or
                     any(len(r) > 1 for r in self.s.groups[c].rows)]
            if not cands:
                return False
            c = max(cands, key=lambda c: self.s.groups[c].w)
            self.measure(c, self.s.groups[c].w - GRID)
        return self.row_w(row) <= max_w

    def row_w(self, row):
        return sum(self.s.groups[c].w for c in row) + max(0, len(row) - 1) * GROUP_GAP

    def row_h(self, row):
        return max(self.s.groups[c].h for c in row) if row else 0

    def pack(self, ids, max_w):
        rows, cur, cur_w = [], [], 0.0
        for c in ids:
            w = self.s.groups[c].w
            add = w if not cur else cur_w + GROUP_GAP + w
            if cur and add > max_w:
                rows.append(cur)
                cur, cur_w = [c], w
            else:
                cur.append(c)
                cur_w = add
        if cur:
            rows.append(cur)
        return rows

    # ---- placing ---------------------------------------------------------------------------
    def place(self, gid: str, x: float, y: float, w: float, h: float):
        g = self.s.groups[gid]
        g.x, g.y, g.w, g.h = x, y, w, h
        head = GROUP_HEAD if g.label else 0
        top = y + GROUP_PAD + head - (10 if head else 0)
        inner_w = w - 2 * GROUP_PAD
        if g.nodes:
            # spread the grid across the available width (up to 1.8x the normal gap)
            gap = NODE_GAP_X
            if g.ncols > 1:
                gap = min(NODE_GAP_X * 2.2, (inner_w - g.ncols * g.nw) / (g.ncols - 1))
                gap = max(NODE_GAP_X, math.floor(gap / GRID) * GRID)
            gw = g.ncols * g.nw + (g.ncols - 1) * gap
            x0 = x + GROUP_PAD + max(0, (inner_w - gw) / 2)
            x0 = math.floor(x0 / GRID) * GRID
            for i, nid in enumerate(g.nodes):
                r, c = divmod(i, g.ncols)
                n = self.s.nodes[nid]
                # centre a short last row
                in_row = min(g.ncols, len(g.nodes) - r * g.ncols)
                off = (g.ncols - in_row) * (g.nw + gap) / 2
                n.x = snap(x0 + off + c * (g.nw + gap) - GRID / 2)
                n.y = snap(top) + r * (g.nh + NODE_GAP_Y)
                n.w, n.h = g.nw, g.nh
            top += g.grid_h + (GROUP_GAP if g.rows else 0)
        self.place_rows(g.rows, x + GROUP_PAD, top, inner_w, y + h - GROUP_PAD - top)

    def place_rows(self, rows, x, y, avail_w, avail_h=None):
        """Place rows of sibling groups; each row is stretched to avail_w and to a common height."""
        cy = y
        heights = [self.row_h(r) for r in rows]
        if avail_h is not None and rows:
            natural = sum(heights) + (len(rows) - 1) * GROUP_GAP
            spare = max(0, avail_h - natural)
            heights[-1] += spare
        for r, rh in zip(rows, heights):
            nat = self.row_w(r)
            extra = max(0, avail_w - nat)
            cx = x
            for i, c in enumerate(r):
                g = self.s.groups[c]
                share = extra * (g.w / (nat - (len(r) - 1) * GROUP_GAP)) if nat else 0
                w = math.floor((g.w + share) / GRID) * GRID
                if i == len(r) - 1:
                    w = x + avail_w - cx
                self.place(c, cx, cy, w, rh)
                cx += w + GROUP_GAP
            cy += rh + GROUP_GAP
        return cy - GROUP_GAP

    def run(self):
        s = self.s
        for gid in s.top:
            self.measure(gid, self.content_w)
        rows = s.rows_hint or self.pack(s.top, self.content_w)
        for r in rows:
            if not self.shrink_row(r, self.content_w):
                print(f"warning: row {r} is wider than width={s.width}; the canvas grows", file=sys.stderr)
        width = max([self.row_w(r) for r in rows] + [self.content_w])
        self.content_w = width
        bottom = self.place_rows(rows, MARGIN, MARGIN + TITLE_H, width)
        self.width = int(width + 2 * MARGIN)
        self.body_bottom = bottom


# --------------------------------------------------------------------------------------------
# Orthogonal edge routing: A* on a GRID-px lattice with bend and crossing penalties.
# Node boxes (plus a clearance) are hard obstacles; group label bands are soft ones.
# --------------------------------------------------------------------------------------------
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]   # E S W N


class Router:
    BEND = 14
    CROSS = 6
    PARALLEL = 60
    HEADER = 60
    NEAR_NODE = 1

    def __init__(self, spec: Spec, width: int, height: int, top: float, bottom: float):
        self.s = spec
        self.W = width // GRID + 2
        self.H = height // GRID + 2
        self.block = bytearray(self.W * self.H)      # 1 = inside a node (+clearance) or off-canvas
        # keep edges inside the drawing area: not in the outer margin, the title or the legend
        lo_x, hi_x = (MARGIN - 20) // GRID, (width - MARGIN + 20) // GRID
        lo_y, hi_y = int(top // GRID), int(bottom // GRID)
        for gy in range(self.H):
            for gx in range(self.W):
                if gx < lo_x or gx > hi_x or gy < lo_y or gy > hi_y:
                    self.block[gx + gy * self.W] = 1
        self.soft = [0] * (self.W * self.H)          # extra cost per cell
        self.used_h = bytearray(self.W * self.H)
        self.used_v = bytearray(self.W * self.H)
        self.used_ports: set = set()
        self.node_cells = {}
        for n in spec.nodes.values():
            x0, y0, x1, y1 = n.rect
            cells = []
            for gx in range(int(x0 // GRID) - 1, int(math.ceil(x1 / GRID)) + 2):
                for gy in range(int(y0 // GRID) - 1, int(math.ceil(y1 / GRID)) + 2):
                    if 0 <= gx < self.W and 0 <= gy < self.H:
                        cells.append(gx + gy * self.W)
            self.node_cells[n.id] = cells
            for c in cells:
                self.block[c] = 1
            # a second, soft ring so edges prefer the middle of gaps
            for gx in range(int(x0 // GRID) - 2, int(math.ceil(x1 / GRID)) + 3):
                for gy in range(int(y0 // GRID) - 2, int(math.ceil(y1 / GRID)) + 3):
                    if 0 <= gx < self.W and 0 <= gy < self.H:
                        self.soft[gx + gy * self.W] += self.NEAR_NODE
        for g in spec.groups.values():
            if not g.label:
                continue
            lw = text_w(g.label, GROUP_PX) * 1.15 + 24
            for gx in range(int(g.x // GRID), int((g.x + lw) // GRID) + 1):
                for gy in range(int(g.y // GRID), int((g.y + GROUP_HEAD) // GRID) + 1):
                    if 0 <= gx < self.W and 0 <= gy < self.H:
                        self.soft[gx + gy * self.W] += self.HEADER
            # crossing a group border costs a little, so edges don't hug borders
            for gx in range(int(g.x // GRID), int((g.x + g.w) // GRID) + 1):
                for gy in (int(round(g.y / GRID)), int(round((g.y + g.h) / GRID))):
                    if 0 <= gx < self.W and 0 <= gy < self.H:
                        self.soft[gx + gy * self.W] += 2
            for gy in range(int(g.y // GRID), int((g.y + g.h) // GRID) + 1):
                for gx in (int(round(g.x / GRID)), int(round((g.x + g.w) / GRID))):
                    if 0 <= gx < self.W and 0 <= gy < self.H:
                        self.soft[gx + gy * self.W] += 2

    def rect_of(self, ref):
        if ref in self.s.nodes:
            return self.s.nodes[ref].rect, self.s.nodes[ref].shape
        g = self.s.groups[ref]
        return g.rect, "group"

    def ports(self, ref):
        """Candidate (boundary point, first outside cell, outward dir index, penalty)."""
        (x0, y0, x1, y1), shape = self.rect_of(ref)
        out = []
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        is_group = shape == "group"
        clear = 1 if is_group else 2   # cells between boundary and first free cell

        def along(a, b, centre_only, frac):
            lo, hi = a + GRID, b - GRID
            mid = (a + b) / 2
            if centre_only:
                return [snap(mid - GRID / 2)]
            span = (b - a) * frac / 2
            lo, hi = max(lo, mid - span), min(hi, mid + span)
            return list(range(snap(lo), int(hi) + 1, GRID))

        top_frac = 0.4 if shape in ("cylinder", "cloud", "hexagon") else 0.8
        side_centre = shape in ("cloud", "hexagon")
        if is_group:
            top_frac = 0.5
        for px in along(x0, x1, False, top_frac):
            pen = abs(px - cx) / GRID * 0.5
            out.append(((px, y0), (px // GRID, int(y0 // GRID) - clear), 3, pen))
            out.append(((px, y1), (px // GRID, int(math.ceil(y1 / GRID)) + clear), 1, pen))
        for py in along(y0, y1, side_centre, 0.7 if not is_group else 0.4):
            pen = abs(py - cy) / GRID * 0.5
            out.append(((x0, py), (int(x0 // GRID) - clear, py // GRID), 2, pen))
            out.append(((x1, py), (int(math.ceil(x1 / GRID)) + clear, py // GRID), 0, pen))
        return [p for p in out if 0 <= p[1][0] < self.W and 0 <= p[1][1] < self.H]

    def route(self, e: Edge):
        W = self.W
        srcs = self.ports(e.src)
        dsts = self.ports(e.dst)
        (tx0, ty0, tx1, ty1), _ = self.rect_of(e.dst)
        tx0, ty0, tx1, ty1 = tx0 / GRID - 2, ty0 / GRID - 2, tx1 / GRID + 2, ty1 / GRID + 2
        goal = {}
        for bp, cell, d, pen in dsts:
            key = cell[0] + cell[1] * W
            arrive = (d + 2) % 4               # direction of travel when entering
            used = 40 if (e.dst, bp) in self.used_ports else 0
            goal[(key, arrive)] = (bp, pen + used)
        heap = []
        best = {}
        parent = {}
        for bp, cell, d, pen in srcs:
            key = cell[0] + cell[1] * W
            if self.block[key]:
                continue
            used = 40 if (e.src, bp) in self.used_ports else 0
            st = (key, d)
            c0 = pen + used
            if c0 < best.get(st, 1e18):
                best[st] = c0
                parent[st] = ("start", bp)
                heapq.heappush(heap, (c0 + self.h(cell[0], cell[1], tx0, ty0, tx1, ty1), c0, st))
        found = None
        while heap:
            f, c, st = heapq.heappop(heap)
            if c > best.get(st, 1e18):
                continue
            if st in goal:
                bp, pen = goal[st]
                total = c + pen
                if found is None or total < found[0]:
                    found = (total, st, bp)
                # keep popping while cheaper candidates remain
                if heap and heap[0][0] >= found[0]:
                    break
                continue
            if found is not None and f >= found[0]:
                break
            key, d = st
            x, y = key % W, key // W
            for nd in (d, (d + 1) % 4, (d + 3) % 4):
                dx, dy = DIRS[nd]
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < self.H):
                    continue
                nk = nx + ny * W
                if self.block[nk] and (nk, nd) not in goal:
                    continue
                cost = 1 + self.soft[nk]
                if nd != d:
                    cost += self.BEND
                    if self.used_h[key] or self.used_v[key]:
                        cost += self.CROSS
                horiz = nd in (0, 2)
                if horiz:
                    if self.used_h[nk]:
                        cost += self.PARALLEL
                    if self.used_v[nk]:
                        cost += self.CROSS
                else:
                    if self.used_v[nk]:
                        cost += self.PARALLEL
                    if self.used_h[nk]:
                        cost += self.CROSS
                ns = (nk, nd)
                nc = c + cost
                if nc < best.get(ns, 1e18):
                    best[ns] = nc
                    parent[ns] = st
                    heapq.heappush(heap, (nc + self.h(nx, ny, tx0, ty0, tx1, ty1), nc, ns))
        if not found:
            # fall back: straight L between centres
            (a0, b0, a1, b1), _ = self.rect_of(e.src)
            (c0, d0, c1, d1), _ = self.rect_of(e.dst)
            p, q = ((a0 + a1) / 2, b1), ((c0 + c1) / 2, d0)
            e.points = [p, (p[0], (p[1] + q[1]) / 2), (q[0], (p[1] + q[1]) / 2), q]
            print(f"warning: no clean route for {e.src}->{e.dst}", file=sys.stderr)
            return
        _, st, end_bp = found
        cells = []
        cur = st
        while True:
            cells.append(cur)
            p = parent[cur]
            if p[0] == "start":
                start_bp = p[1]
                break
            cur = p
        cells.reverse()
        pts = [start_bp] + [((k % W) * GRID, (k // W) * GRID) for k, _ in cells] + [end_bp]
        # mark usage
        for (k, d) in cells:
            if d in (0, 2):
                self.used_h[k] = 1
            else:
                self.used_v[k] = 1
        self.used_ports.add((e.src, start_bp))
        self.used_ports.add((e.dst, end_bp))
        e.points = simplify(pts)
        (sx0, sy0, sx1, sy1), _ = self.rect_of(e.src)
        (dx0, dy0, dx1, dy1), _ = self.rect_of(e.dst)
        e.src_port = ((start_bp[0] - sx0) / (sx1 - sx0), (start_bp[1] - sy0) / (sy1 - sy0))
        e.dst_port = ((end_bp[0] - dx0) / (dx1 - dx0), (end_bp[1] - dy0) / (dy1 - dy0))

    @staticmethod
    def h(x, y, x0, y0, x1, y1):
        dx = x0 - x if x < x0 else (x - x1 if x > x1 else 0)
        dy = y0 - y if y < y0 else (y - y1 if y > y1 else 0)
        return dx + dy


def simplify(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if p == out[-1]:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                out[-1] = p
                continue
        out.append(p)
    return out


def overlaps(a, b, pad=0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def place_labels(spec: Spec, edges, width: int):
    boxes = [n.rect for n in spec.nodes.values()]
    heads = [(g.x, g.y, g.x + text_w(g.label, GROUP_PX) * 1.15 + 24, g.y + GROUP_HEAD)
             for g in spec.groups.values() if g.label]
    taken = []
    for e in edges:
        if not e.label:
            continue
        lw = text_w(e.label, EDGE_PX) + 10
        lh = EDGE_PX + 6
        segs = []
        pts = e.points
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            segs.append((L, i, a, b))
        cands = []

        def fits(seg):
            L, _, a, b = seg
            return L >= ((lw if a[1] == b[1] else lh) + 16)
        ordered = sorted(segs, key=lambda sg: (not fits(sg), -sg[0]))
        for L, i, a, b in ordered:
            for t in (0.5, 0.35, 0.65, 0.25, 0.75, 0.15, 0.85):
                cx = a[0] + (b[0] - a[0]) * t
                cy = a[1] + (b[1] - a[1]) * t
                cands.append((cx, cy))
        for L, i, a, b in ordered:
            # beside the line instead of on it
            cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if a[1] == b[1]:
                cands += [(cx, cy - lh / 2 - 3), (cx, cy + lh / 2 + 3)]
            else:
                cands += [(cx + lw / 2 + 4, cy), (cx - lw / 2 - 4, cy)]
        chosen = None
        for strict in (True, False):
            for cx, cy in cands:
                box = (cx - lw / 2, cy - lh / 2, cx + lw / 2, cy + lh / 2)
                if box[0] < 4 or box[2] > width - 4:
                    continue
                if any(overlaps(box, r, 2) for r in boxes + taken):
                    continue
                if strict and any(overlaps(box, r) for r in heads):
                    continue
                chosen = (cx, cy, box)
                break
            if chosen:
                break
        if not chosen:
            cx, cy = cands[0]
            chosen = (cx, cy, (cx - lw / 2, cy - lh / 2, cx + lw / 2, cy + lh / 2))
            print(f"warning: label '{e.label}' could not avoid every box", file=sys.stderr)
        e.label_pos = (chosen[0], chosen[1])
        e.label_box = chosen[2]
        taken.append(chosen[2])


def path_fraction(pts, p):
    """Position of point p along the polyline as a value in [0, 1]."""
    total, acc, at = 0.0, 0.0, None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if at is None and min(a[0], b[0]) - 0.5 <= p[0] <= max(a[0], b[0]) + 0.5 \
                and min(a[1], b[1]) - 0.5 <= p[1] <= max(a[1], b[1]) + 0.5:
            at = acc + abs(p[0] - a[0]) + abs(p[1] - a[1])
        acc += L
    total = acc
    return (at / total) if (total and at is not None) else 0.5


# --------------------------------------------------------------------------------------------
# Legend
# --------------------------------------------------------------------------------------------
def legend_items(spec: Spec):
    seen = []
    for g in spec.groups.values():
        if g.id != "__loose" and g.role not in seen:
            seen.append(g.role)
    return [(r, ROLES[r][2]) for r in seen]


def legend_layout(spec: Spec, y: float, width: int):
    """Legend entries as (role, name, x, y) plus the two edge styles; wraps onto more lines if needed."""
    items = legend_items(spec)
    x0 = MARGIN + text_w("Legend", 12) + 16
    entries = [("role", r, n, 22 + text_w(n, 12) + 24) for r, n in items]
    entries += [("edge", "solid", "flow / call", 34 + text_w("flow / call", 12) + 24),
                ("edge", "dashed", "provisions / optional", 34 + text_w("provisions / optional", 12) + 24)]
    out, extra, x, cy = [], [], x0, y
    for kind, key, name, w in entries:
        if x + w > width - MARGIN and x > x0:
            x, cy = x0, cy + 24
        if kind == "role":
            out.append((key, name, x, cy))
        else:
            extra.append((key, name, x, cy))
        x += w
    return out, extra


def legend_height(spec: Spec, width: int) -> int:
    out, extra = legend_layout(spec, 0, width)
    return int(max(p[-1] for p in out + extra)) + 16


# --------------------------------------------------------------------------------------------
# SVG
# --------------------------------------------------------------------------------------------
def shape_svg(n: Node, stroke: str) -> str:
    x, y, w, h = n.x, n.y, n.w, n.h
    fill = "#FFFFFF"
    sw = 1.4
    if n.shape == "cylinder":
        ry = 7
        return (f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0,0 {w},0 a{w/2},{ry} 0 0,0 {-w},0 Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0,1 {w},0 v{h-2*ry} a{w/2},{ry} 0 0,1 {-w},0 Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<path d="M{x},{y+ry} a{w/2},{ry} 0 0,0 {w},0" fill="none" stroke="{stroke}" stroke-width="{sw}"/>')
    if n.shape == "hexagon":
        k = 16
        pts = [(x + k, y), (x + w - k, y), (x + w, y + h / 2), (x + w - k, y + h), (x + k, y + h), (x, y + h / 2)]
        return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    if n.shape == "cloud":
        # a cloud whose extremes touch the middle of each bbox side
        def P(fx, fy):
            return f"{x + fx * w:.1f},{y + fy * h:.1f}"
        d = (f"M{P(0.14,0.72)} "
             f"C{P(-0.02,0.72)} {P(-0.02,0.40)} {P(0.14,0.38)} "
             f"C{P(0.14,0.10)} {P(0.36,0.02)} {P(0.46,0.14)} "
             f"C{P(0.52,-0.04)} {P(0.78,-0.02)} {P(0.80,0.22)} "
             f"C{P(1.02,0.20)} {P(1.02,0.62)} {P(0.86,0.66)} "
             f"C{P(0.92,0.92)} {P(0.66,1.04)} {P(0.56,0.86)} "
             f"C{P(0.46,1.04)} {P(0.18,1.00)} {P(0.14,0.72)} Z")
        return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def node_text_svg(n: Node) -> str:
    lh, sh = 17, 15
    total = len(n.lines) * lh + len(n.sublines) * sh
    cy = n.y + n.h / 2 + (3 if n.shape == "cylinder" else 0)
    y = cy - total / 2 + 12.5
    out = []
    for ln in n.lines:
        out.append(f'<text x="{n.x + n.w/2:.1f}" y="{y:.1f}" text-anchor="middle" font-size="{LABEL_PX}" '
                   f'font-weight="600" fill="{TEXT_COLOR}">{escape(ln)}</text>')
        y += lh
    for ln in n.sublines:
        out.append(f'<text x="{n.x + n.w/2:.1f}" y="{y - 1:.1f}" text-anchor="middle" font-size="{SUB_PX}" '
                   f'fill="{SUBTEXT_COLOR}">{escape(ln)}</text>')
        y += sh
    return "".join(out)


def depth(spec, g):
    d = 0
    while g.parent:
        d += 1
        g = spec.groups[g.parent]
    return d


def write_svg(spec: Spec, lay: Layout, height: int, path: str):
    W = lay.width
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" '
         f'font-family="{escape(FONT)}">',
         f'<title>{escape(spec.title)}</title>',
         '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE_COLOR}"/></marker></defs>',
         f'<rect x="0" y="0" width="{W}" height="{height}" fill="#FFFFFF"/>',
         f'<text x="{MARGIN}" y="{MARGIN + 10}" font-size="20" font-weight="700" fill="{TEXT_COLOR}">{escape(spec.title)}</text>']
    if spec.subtitle:
        o.append(f'<text x="{MARGIN}" y="{MARGIN + 32}" font-size="13" fill="{SUBTEXT_COLOR}">{escape(spec.subtitle)}</text>')
    for g in sorted(spec.groups.values(), key=lambda g: depth(spec, g)):
        if not g.label:
            continue
        fill, stroke, _ = ROLES[g.role]
        o.append(f'<g id="group-{escape(g.id)}"><rect x="{g.x}" y="{g.y}" width="{g.w}" height="{g.h}" rx="8" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>'
                 f'<text x="{g.x + 12}" y="{g.y + 20}" font-size="{GROUP_PX}" font-weight="700" fill="{stroke}">'
                 f'{escape(g.label)}</text></g>')
    for n in spec.nodes.values():
        stroke = ROLES[spec.groups[n.group].role][1]
        o.append(f'<g id="node-{escape(n.id)}">{shape_svg(n, stroke)}{node_text_svg(n)}</g>')
    for e in spec.edges:
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in e.points)
        dash = ' stroke-dasharray="6 4"' if e.dashed else ""
        o.append(f'<path d="{d}" fill="none" stroke="{EDGE_COLOR}" stroke-width="1.4"{dash} '
                 f'marker-end="url(#arrow)"/>')
    for e in spec.edges:
        if e.label and e.label_box:
            x0, y0, x1, y1 = e.label_box
            o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1-x0:.1f}" height="{y1-y0:.1f}" rx="3" fill="#FFFFFF" '
                     f'fill-opacity="0.92"/>'
                     f'<text x="{e.label_pos[0]:.1f}" y="{e.label_pos[1] + 4:.1f}" text-anchor="middle" '
                     f'font-size="{EDGE_PX}" fill="{EDGE_COLOR}">{escape(e.label)}</text>')
    # legend
    ly = lay.legend_y
    items, extra = legend_layout(spec, ly, W)
    o.append(f'<text x="{MARGIN}" y="{ly + 12}" font-size="12" font-weight="700" fill="{TEXT_COLOR}">Legend</text>')
    for role, name, x, y in items:
        fill, stroke, _ = ROLES[role]
        o.append(f'<rect x="{x}" y="{y}" width="16" height="16" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>'
                 f'<text x="{x + 22}" y="{y + 12}" font-size="12" fill="{TEXT_COLOR}">{escape(name)}</text>')
    for kind, name, x, ey in extra:
        dash = ' stroke-dasharray="6 4"' if kind == "dashed" else ""
        o.append(f'<path d="M{x},{ey + 8} L{x + 28},{ey + 8}" stroke="{EDGE_COLOR}" stroke-width="1.4"{dash} '
                 f'marker-end="url(#arrow)"/><text x="{x + 34}" y="{ey + 12}" font-size="12" fill="{TEXT_COLOR}">'
                 f'{escape(name)}</text>')
    o.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o) + "\n")


# --------------------------------------------------------------------------------------------
# draw.io
# --------------------------------------------------------------------------------------------
def xml_attr(s: str) -> str:
    return escape(s, {'"': "&quot;", "\n": "&#10;"})


def write_drawio(spec: Spec, lay: Layout, height: int, path: str):
    W = lay.width
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']

    def cid(ref):
        return ("g_" if ref in spec.groups else "n_") + re.sub(r"[^A-Za-z0-9_.-]", "_", ref)

    cells.append(f'<mxCell id="title" value="{xml_attr(spec.title)}" style="text;html=1;fontSize=20;fontStyle=1;'
                 f'align=left;verticalAlign=middle;fontColor={TEXT_COLOR};" vertex="1" parent="1">'
                 f'<mxGeometry x="{MARGIN}" y="{MARGIN - 8}" width="{W - 2 * MARGIN}" height="28" as="geometry"/></mxCell>')
    if spec.subtitle:
        cells.append(f'<mxCell id="subtitle" value="{xml_attr(spec.subtitle)}" style="text;html=1;fontSize=13;'
                     f'align=left;verticalAlign=middle;fontColor={SUBTEXT_COLOR};" vertex="1" parent="1">'
                     f'<mxGeometry x="{MARGIN}" y="{MARGIN + 20}" width="{W - 2 * MARGIN}" height="20" as="geometry"/></mxCell>')
    for g in sorted(spec.groups.values(), key=lambda g: depth(spec, g)):
        if not g.label:
            continue
        fill, stroke, _ = ROLES[g.role]
        par = spec.groups[g.parent] if g.parent else None
        px, py = (par.x, par.y) if par else (0, 0)
        style = (f"swimlane;html=1;whiteSpace=wrap;startSize={GROUP_HEAD};rounded=1;arcSize=2;absoluteArcSize=1;"
                 f"fillColor={fill};swimlaneFillColor={fill};strokeColor={stroke};fontColor={stroke};"
                 f"fontStyle=1;fontSize={GROUP_PX};align=left;spacingLeft=10;swimlaneLine=0;collapsible=0;"
                 f"container=1;fontFamily=Helvetica;")
        cells.append(f'<mxCell id="{cid(g.id)}" value="{xml_attr(g.label)}" style="{style}" vertex="1" '
                     f'parent="{cid(g.parent) if g.parent else "1"}">'
                     f'<mxGeometry x="{g.x - px}" y="{g.y - py}" width="{g.w}" height="{g.h}" as="geometry"/></mxCell>')
    shape_style = {
        "box": "rounded=1;arcSize=10;",
        "cylinder": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=7;",
        "cloud": "ellipse;shape=cloud;",
        "hexagon": "shape=hexagon;perimeter=hexagonPerimeter2;size=16;fixedSize=1;",
    }
    for n in spec.nodes.values():
        g = spec.groups[n.group]
        stroke = ROLES[g.role][1]
        px, py = (g.x, g.y) if g.label else (0, 0)
        value = f"<b>{escape(n.label)}</b>"
        if n.sublabel:
            value += f'<br><font style="font-size:{SUB_PX}px" color="{SUBTEXT_COLOR}">{escape(n.sublabel)}</font>'
        style = (shape_style[n.shape] + f"whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor={stroke};"
                 f"fontColor={TEXT_COLOR};fontSize={LABEL_PX};strokeWidth=1.4;")
        cells.append(f'<mxCell id="{cid(n.id)}" value="{xml_attr(value)}" style="{style}" vertex="1" '
                     f'parent="{cid(n.group) if g.label else "1"}">'
                     f'<mxGeometry x="{n.x - px}" y="{n.y - py}" width="{n.w}" height="{n.h}" as="geometry"/></mxCell>')
    for i, e in enumerate(spec.edges):
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;"
                 f"endFill=1;strokeColor={EDGE_COLOR};strokeWidth=1.4;fontSize={EDGE_PX};fontColor={EDGE_COLOR};"
                 f"labelBackgroundColor=#FFFFFF;")
        if e.dashed:
            style += "dashed=1;dashPattern=6 4;"
        if e.src_port:
            style += f"exitX={e.src_port[0]:.4f};exitY={e.src_port[1]:.4f};exitDx=0;exitDy=0;"
        if e.dst_port:
            style += f"entryX={e.dst_port[0]:.4f};entryY={e.dst_port[1]:.4f};entryDx=0;entryDy=0;"
        pts = "".join(f'<mxPoint x="{x:.1f}" y="{y:.1f}"/>' for x, y in e.points[1:-1])
        rel = 0
        if e.label and e.label_pos:
            rel = 2 * path_fraction(e.points, e.label_pos) - 1
        cells.append(f'<mxCell id="e_{i}" value="{xml_attr(e.label)}" style="{style}" edge="1" parent="1" '
                     f'source="{cid(e.src)}" target="{cid(e.dst)}">'
                     f'<mxGeometry x="{rel:.3f}" relative="1" as="geometry">'
                     f'<Array as="points">{pts}</Array><mxPoint as="offset"/></mxGeometry></mxCell>')
    # legend
    ly = lay.legend_y
    items, extra = legend_layout(spec, ly, W)
    cells.append(f'<mxCell id="legend_t" value="Legend" style="text;html=1;fontSize=12;fontStyle=1;align=left;'
                 f'verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{MARGIN}" y="{ly - 2}" width="60" '
                 f'height="20" as="geometry"/></mxCell>')
    for j, (role, name, x, y) in enumerate(items):
        fill, stroke, _ = ROLES[role]
        cells.append(f'<mxCell id="legend_s{j}" value="" style="rounded=1;arcSize=15;fillColor={fill};strokeColor={stroke};" '
                     f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="16" height="16" as="geometry"/></mxCell>')
        cells.append(f'<mxCell id="legend_l{j}" value="{xml_attr(name)}" style="text;html=1;fontSize=12;align=left;'
                     f'verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x + 20}" y="{y - 2}" '
                     f'width="{text_w(name, 12) + 16:.0f}" height="20" as="geometry"/></mxCell>')
    for j, (kind, name, x, ey) in enumerate(extra):
        dash = "dashed=1;dashPattern=6 4;" if kind == "dashed" else ""
        cells.append(f'<mxCell id="legend_e{j}" value="" style="endArrow=block;endFill=1;html=1;strokeColor={EDGE_COLOR};'
                     f'{dash}" edge="1" parent="1"><mxGeometry relative="1" as="geometry">'
                     f'<mxPoint x="{x}" y="{ey + 8}" as="sourcePoint"/><mxPoint x="{x + 28}" y="{ey + 8}" as="targetPoint"/>'
                     f'</mxGeometry></mxCell>')
        cells.append(f'<mxCell id="legend_el{j}" value="{xml_attr(name)}" style="text;html=1;fontSize=12;align=left;'
                     f'verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="{x + 32}" y="{ey - 2}" '
                     f'width="{text_w(name, 12) + 16:.0f}" height="20" as="geometry"/></mxCell>')
    name = xml_attr(spec.title)
    doc = (f'<mxfile host="diagram.py" type="device">\n'
           f'  <diagram id="d1" name="{name}">\n'
           f'    <mxGraphModel dx="{W}" dy="{height}" grid="1" gridSize={GRID!r} guides="1" tooltips="1" connect="1" '
           f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{height}" math="0" shadow="0" '
           f'background="#FFFFFF">\n      <root>\n        ' + "\n        ".join(cells) +
           "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n")
    doc = doc.replace(f"gridSize={GRID!r}", f'gridSize="{GRID}"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)


# --------------------------------------------------------------------------------------------
# PNG via Playwright
# --------------------------------------------------------------------------------------------
def find_chromium():
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "/opt/pw-browsers",
             os.path.expanduser("~/.cache/ms-playwright")]
    pats = ["chromium-*/chrome-linux*/chrome", "chromium_headless_shell-*/chrome-linux*/headless_shell",
            "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"]
    for r in roots:
        if not r:
            continue
        for p in pats:
            hits = sorted(glob.glob(os.path.join(r, p)))
            if hits:
                return hits[-1]
    for name in ("chromium", "chromium-browser", "google-chrome"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def render_png(svg_path: str, png_path: str, width: int, height: int) -> bool:
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and os.path.isdir("/opt/pw-browsers"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"
    html = ("<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;background:#fff}"
            "img{display:block}</style></head><body>"
            f"<img src='file://{os.path.abspath(svg_path)}' width='{width}' height='{height}'></body></html>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as t:
        t.write(html)
        page_path = t.name
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            sync_playwright = None
        if sync_playwright:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch()
                except Exception:
                    exe = find_chromium()
                    if not exe:
                        raise
                    browser = p.chromium.launch(executable_path=exe)
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=2)
                page.goto("file://" + page_path)
                page.wait_for_load_state("load")
                page.screenshot(path=png_path, clip={"x": 0, "y": 0, "width": width, "height": height})
                browser.close()
            return True
        if shutil.which("node"):
            js = f"""
const pw = require('playwright');
(async () => {{
  let b; try {{ b = await pw.chromium.launch(); }} catch (e) {{ b = await pw.chromium.launch({{executablePath: {repr(find_chromium() or '')}}}); }}
  const p = await b.newPage({{viewport: {{width: {width}, height: {height}}}, deviceScaleFactor: 2}});
  await p.goto('file://{page_path}');
  await p.screenshot({{path: {repr(os.path.abspath(png_path))}, clip: {{x: 0, y: 0, width: {width}, height: {height}}}}});
  await b.close();
}})().catch(e => {{ console.error(e); process.exit(1); }});
"""
            r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
            if r.returncode == 0:
                return True
            print("node playwright failed: " + r.stderr.strip()[:400], file=sys.stderr)
        print("PNG skipped: install Python Playwright (pip install playwright) or Node Playwright", file=sys.stderr)
        return False
    finally:
        os.unlink(page_path)


# --------------------------------------------------------------------------------------------
def build(spec_path: str, outdir: str, name: str | None = None, png: bool = True):
    with open(spec_path, encoding="utf-8") as f:
        spec = Spec(yaml.safe_load(f))
    lay = Layout(spec)
    lay.run()
    lay.legend_y = snap(lay.body_bottom + 30)
    height = int(lay.legend_y + legend_height(spec, lay.width) + MARGIN)
    router = Router(spec, lay.width, height, MARGIN + TITLE_H - 20, lay.legend_y - 10)
    # route short edges first: they have the fewest options
    def est(e):
        (a0, b0, a1, b1), _ = router.rect_of(e.src)
        (c0, d0, c1, d1), _ = router.rect_of(e.dst)
        return abs((a0 + a1) - (c0 + c1)) + abs((b0 + b1) - (d0 + d1))
    for e in sorted(spec.edges, key=est):
        router.route(e)
    place_labels(spec, spec.edges, lay.width)
    os.makedirs(outdir, exist_ok=True)
    name = name or os.path.splitext(os.path.basename(spec_path))[0]
    base = os.path.join(outdir, name)
    write_drawio(spec, lay, height, base + ".drawio")
    write_svg(spec, lay, height, base + ".svg")
    made = [base + ".drawio", base + ".svg"]
    if png and render_png(base + ".svg", base + ".png", lay.width, height):
        made.append(base + ".png")
    for m in made:
        print("wrote", m)
    return made


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("spec")
    ap.add_argument("outdir")
    ap.add_argument("--name", help="output base name (default: spec file name)")
    ap.add_argument("--no-png", action="store_true", help="skip the PNG render")
    a = ap.parse_args()
    build(a.spec, a.outdir, a.name, not a.no_png)


if __name__ == "__main__":
    main()
