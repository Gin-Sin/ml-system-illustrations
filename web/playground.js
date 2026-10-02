import {
  Scene, VGroup, Rectangle, Line, Arrow, Dot, Text,
  FadeOut, Indicate, Shift, Clickable,
} from "manim-web";

const INK = "#f5f3ef", MUTED = "#aaa7a0", EDGE = "#343434", GOLD = "#ffff80";
const COLORS = { A: "#58c4dd", B: "#c792ea", C: "#5cd0b3", D: "#f28d9b" };
const point = (x, y) => [x, y, 0];

function label(text, x, y, { size = 23, color = INK, code = false } = {}) {
  return new Text({
    text: String(text), fontSize: size, color,
    fontFamily: code ? "JetBrains Mono" : "CMU Serif",
  }).moveTo(point(x, y));
}

function strip(tokens, size, x, y, width, color, active = -1, textScale = 1) {
  const group = new VGroup(), cells = [];
  const cellWidth = width / size;
  for (let i = 0; i < size; i++) {
    const cx = x - width / 2 + cellWidth * (i + 0.5);
    const used = i < tokens.length;
    const cell = new Rectangle({
      width: cellWidth, height: 0.43, center: point(cx, y),
      color: i === active ? GOLD : used ? color : EDGE,
      fillOpacity: i === active ? 0.22 : used ? 0.09 : 0,
      strokeWidth: i === active ? 2.3 : 1.2,
    });
    group.add(cell);
    const text = used ? label(String(tokens[i]).replace(/^[A-D]/, ""), cx, y, {
      code: true, size: (size === 8 ? 18 : 21) * textScale, color: i === active ? GOLD : color,
    }) : null;
    if (text) group.add(text);
    cells.push({ object: cell, text, position: point(cx, y) });
  }
  return { group, cells };
}

/** Live Manim objects, rendered and animated by manim-web's Scene. */
export class PagedAttentionPlayground {
  constructor(container, { onToken, onPhase }) {
    this.container = container;
    this.onToken = onToken;
    this.onPhase = onPhase;
    this.clickables = [];
    this.busy = false;
    this.scene = new Scene(container, {
      width: Math.max(1, container.clientWidth), height: 560,
      backgroundColor: "#000000", autoRender: false,
      autoResize: false, frameWidth: 14, frameHeight: 8,
    });
    const canvas = this.scene.renderer.getCanvas();
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Animated logical blocks, block table, and GPU memory. Use the token slider or the text view for keyboard access.");
    container.dataset.engine = "manim-web";
    this.observer = new ResizeObserver(() => {
      if (this.busy) this.resizePending = true;
      else if (this.state && Math.abs(container.clientWidth - this.pixelWidth) > 1) this.draw(this.state);
    });
    this.observer.observe(container);
  }

  layout(state) {
    const request = state.requests.find(r => r.id === state.selected);
    const rows = Math.max(2, request?.table.length ?? 0);
    const mobile = this.container.clientWidth < 680;
    const height = mobile ? 10.0 + rows * 0.69 : Math.max(7.8, 2.4 + rows * 0.64);
    const width = mobile ? 7.1 : 14;
    const top = height / 2 - 0.7;
    return {
      width, height, mobile, rows, top,
      logicalX: mobile ? -1.25 : -4.65,
      tableX: mobile ? 2.25 : -0.75,
      rowY: b => top - 1.05 - b * (mobile ? 0.69 : 0.64),
      poolTop: mobile ? top - rows * 0.69 - 2.0 : top,
      physical: p => point((mobile ? -1.65 : 2.0) + (p % 2) * 3.3,
        (mobile ? top - rows * 0.69 - 2.0 : top) - 1.2 - Math.floor(p / 2) * 0.92),
    };
  }

  draw(state) {
    if (this.disposed) return;
    this.state = state;
    for (const clickable of this.clickables) clickable.dispose();
    this.clickables = [];
    this.scene.clear({ render: false });
    this.geometry = this.layout(state);
    const g = this.geometry;
    const text = (value, x, y, options = {}) => label(value, x, y, {
      ...options, size: (options.size ?? 23) * (g.mobile ? options.code ? 1.45 : 1.2 : 1),
    });
    this.pixelWidth = this.container.clientWidth;
    const pixelHeight = Math.round(this.pixelWidth * g.height / g.width);
    this.container.style.height = `${pixelHeight}px`;
    this.scene.camera.frameHeight = g.height;
    this.scene.camera.frameWidth = g.width;
    this.scene.resize(this.pixelWidth, pixelHeight);
    this.physical = new Map();
    this.logical = new Map();
    this.tables = new Map();
    const request = state.requests.find(r => r.id === state.selected);
    const selectedBlock = Math.floor(state.token / state.blockSize);
    const offset = state.token % state.blockSize;
    const selectedPhysical = request?.table[selectedBlock];
    const requestColor = COLORS[state.selected] ?? INK;
    this.scene.add(
      text("Logical token order", g.logicalX, g.top, { size: 30 }),
      text("Block table", g.tableX, g.top, { size: 27 }),
      text("GPU memory", g.mobile ? 0 : 3.65, g.poolTop, { size: 30 }),
      text("logical → physical", g.tableX, g.top - 0.43, { size: 17, color: MUTED }),
      text("12 physical blocks · allocate anywhere", g.mobile ? 0 : 3.65, g.poolTop - 0.43, { size: 20, color: MUTED }),
    );

    request?.table.forEach((physical, b) => {
      const y = g.rowY(b);
      const tokens = state.pool[physical].tokens.map((_, i) => b * state.blockSize + i);
      const block = strip(tokens, state.blockSize, g.logicalX, y, 3.1, requestColor,
        b === selectedBlock ? offset : -1, g.mobile ? 1.45 : 1);
      this.scene.add(block.group, text(`L${b}`, g.logicalX - 1.83, y, { code: true, size: 19, color: MUTED }));
      this.logical.set(b, block);
      block.cells.forEach((cell, i) => {
        if (i < tokens.length) this.clickables.push(new Clickable(cell.object, this.scene, {
          onClick: () => { if (!this.busy) this.onToken(b * state.blockSize + i); },
        }));
      });
      const table = new VGroup(
        new Rectangle({ width: 1.6, height: 0.43, center: point(g.tableX, y),
          color: b === selectedBlock ? GOLD : EDGE, strokeWidth: 1.3, fillOpacity: 0 }),
        text(`${b} → ${physical}`, g.tableX, y, { code: true, size: 21, color: b === selectedBlock ? GOLD : MUTED }),
      );
      this.scene.add(table);
      this.tables.set(b, table);
      this.clickables.push(new Clickable(table, this.scene, {
        onClick: () => { if (!this.busy) this.onToken(b * state.blockSize); },
      }));
    });
    if (!request) this.scene.add(text("All requests finished.", g.logicalX, g.rowY(0), { size: 23, color: MUTED }));

    state.pool.forEach((p, index) => {
      const [x, y] = g.physical(index);
      const color = p.refs > 1 ? GOLD : COLORS[p.owners[0]] ?? EDGE;
      const block = strip(p.tokens, state.blockSize, x, y, 2.8, color,
        index === selectedPhysical ? offset : -1, g.mobile ? 1.45 : 1);
      const address = text(`P${index}`, x - 1.15, y + 0.37, { code: true, size: 19, color: p.refs ? color : MUTED });
      const refs = text(p.refs ? `${p.owners.join("/")} · ${g.mobile ? "" : "refs "}${p.refs}` : "free", x + 0.52, y + 0.37,
        { code: true, size: 16, color: p.refs ? color : MUTED });
      this.scene.add(block.group, address, refs);
      this.physical.set(index, { ...block, refs, address });
      const logical = request?.table.indexOf(index) ?? -1;
      if (logical >= 0) block.cells.forEach((cell, i) => {
        if (i < p.tokens.length) this.clickables.push(new Clickable(cell.object, this.scene, {
          onClick: () => { if (!this.busy) this.onToken(logical * state.blockSize + i); },
        }));
      });
    });

    this.route = [];
    if (request?.length) {
      const source = this.logical.get(selectedBlock).cells[offset].position;
      const dest = this.physical.get(selectedPhysical).cells[offset].position;
      const row = g.rowY(selectedBlock);
      // Route below the physical row to keep its address and owners unobstructed.
      const gutter = g.mobile ? 3.4 : 0.35;
      this.route = [source, point(g.logicalX + 1.68, row), point(g.tableX - 0.9, row),
        point(g.tableX + 0.9, row), point(gutter, row), point(gutter, dest[1] - 0.38),
        point(dest[0], dest[1] - 0.38), point(dest[0], dest[1] - 0.23)];
      const visible = [
        [this.route[1], this.route[2]],
        [this.route[3], this.route[4]], [this.route[4], this.route[5]],
        [this.route[5], this.route[6]],
      ];
      for (const [start, end] of visible) this.scene.add(new Line({ start, end, color: GOLD, strokeWidth: 1.1 }));
      this.scene.add(new Arrow({ start: this.route[6], end: this.route[7], color: GOLD, strokeWidth: 1.3, tipLength: 0.11, tipWidth: 0.055 }));
    }
    this.scene.render();
    this.container.dataset.state = this.busy ? "animating" : "ready";
  }

  async travel(points, duration = 1.1) {
    const dot = new Dot({ radius: 0.065, color: GOLD }).moveTo(points[0]);
    this.scene.add(dot);
    // Weight the time by distance so turns do not create jumps in speed.
    const lengths = points.slice(1).map((p, i) => Math.hypot(p[0] - points[i][0], p[1] - points[i][1]));
    const total = lengths.reduce((a, b) => a + b, 0) || 1;
    for (let i = 1; i < points.length; i++) {
      if (this.disposed) return;
      if (lengths[i - 1] < 0.001) continue;
      await this.scene.play(new Shift(dot, {
        direction: points[i].map((v, axis) => v - points[i - 1][axis]),
        duration: Math.max(0.05, duration * lengths[i - 1] / total),
      }));
    }
    this.scene.remove(dot);
    dot.dispose();
  }

  async transition(before, after, action, animate) {
    this.busy = true;
    this.container.dataset.state = "animating";
    try {
      if (!animate) { this.draw(after); return; }
      const request = after.requests.find(r => r.id === after.selected);
      const old = before.requests.find(r => r.id === after.selected);
      const tail = request?.table.at(-1);
      const oldTail = old?.table.at(-1);
      if (action === "append" && old && old.length % after.blockSize !== 0 && tail !== oldTail) {
        this.draw(before);
        this.container.dataset.state = "animating";
        this.onPhase(`Copy P${oldTail} into P${tail}. The shared original stays in place.`);
        const [x, y] = this.geometry.physical(oldTail);
        const [tx, ty] = this.geometry.physical(tail);
        const ghost = strip(before.pool[oldTail].tokens, before.blockSize, x, y, 2.8, COLORS[after.selected], -1, this.geometry.mobile ? 1.45 : 1).group;
        this.scene.add(ghost);
        await this.scene.play(new Shift(ghost, { direction: [tx - x, ty - y, 0], duration: 1.05 }));
        this.scene.remove(ghost);
        ghost.dispose();
        const redirected = structuredClone(after);
        redirected.requests.find(r => r.id === after.selected).length--;
        redirected.pool[tail].tokens.pop();
        redirected.token = old.length - 1;
        this.draw(redirected);
        this.onPhase(`Redirect the block table to P${tail}. The copied prefix is ready.`);
        await this.scene.play(new Indicate(this.tables.get(request.table.length - 1), { duration: 0.45, color: GOLD, scaleFactor: 1.06 }));
        this.draw(after);
        const written = this.physical.get(tail).cells[after.token % after.blockSize].text;
        written.opacity = 0;
        this.onPhase(`Write token ${after.token} into P${tail}. The sibling still reads P${oldTail}.`);
        await this.travel(this.route, 0.65);
        written.opacity = 1;
      } else if (action === "release") {
        this.draw(before);
        this.onPhase("Release a block only when its last reference disappears.");
        const freed = before.pool.flatMap((p, i) => p.refs && !after.pool[i].refs ? [i] : []);
        if (freed.length) await this.scene.play(...freed.map(i => new FadeOut(this.physical.get(i).group, { duration: 0.65 })));
        this.draw(after);
      } else {
        this.draw(after);
        if (action === "fork") {
          this.onPhase("Share the same physical blocks. Increase their reference counts.");
          await this.scene.play(...request.table.map(i => new Indicate(this.physical.get(i).refs,
            { duration: 0.85, color: GOLD, scaleFactor: 1.14 })));
        } else if (action === "append" || action === "lookup") {
          const written = action === "append" ? this.physical.get(tail).cells[after.token % after.blockSize].text : null;
          if (written) written.opacity = 0;
          this.onPhase(action === "lookup" ? "Follow the token through the block table to its physical slot."
            : old?.length % after.blockSize === 0 ? `Allocate P${tail} at the block boundary, then write the new KV entry.`
              : "Write into the existing tail block. No allocation is needed.");
          if (action === "append" && old?.length % after.blockSize === 0) {
            await this.scene.play(new Indicate(this.physical.get(tail).group, { duration: 0.45, color: GOLD, scaleFactor: 1.05 }));
          }
          if (this.route.length) await this.travel(this.route);
          if (written) written.opacity = 1;
        }
      }
    } finally {
      this.busy = false;
      this.draw(after);
      this.resizePending = false;
      if (!this.disposed) this.onPhase("Click a token or block-table entry to inspect its address.");
    }
  }

  dispose() {
    this.disposed = true;
    this.observer.disconnect();
    for (const clickable of this.clickables) clickable.dispose();
    this.scene.dispose();
  }
}
