import { Allocator } from "./allocator.js";

const $ = (id) => document.getElementById(id);
const colors = { A: "#58c4dd", B: "#c792ea", C: "#5cd0b3", D: "#f28d9b" };
let model = new Allocator(),
  selected = "A",
  token = 0;
let playground = null, busy = false;
$("animate").checked = !matchMedia("(prefers-reduced-motion: reduce)").matches;

function snapshot() {
  return {
    selected, token, blockSize: model.blockSize,
    requests: [...model.requests].map(([id, r]) => ({ id, length: r.length, table: [...r.table] })),
    pool: model.pool.map((p, i) => ({ tokens: [...p.tokens], refs: p.refs, owners: model.owners(i) })),
  };
}

function setBusy(value) {
  busy = value;
  $("manim-stage").setAttribute("aria-busy", String(value));
  for (const control of document.querySelectorAll(".lab-toolbar button, .lab-toolbar select, .actions button, .scene-controls input, .scene-controls button, #block-table button")) {
    control.disabled = value;
  }
  if (!value) render();
}

function useTextView(error) {
  console.error("Interactive scene unavailable", error);
  playground?.dispose();
  playground = null;
  $("manim-stage").replaceChildren();
  $("manim-stage").style.height = "0";
  $("manim-stage").dataset.state = "unavailable";
  $("memory-data").open = true;
  $("motion-caption").textContent = "The animated view is unavailable in this browser. You can still explore every operation in the text view below.";
}

async function updateScene(before, action) {
  if (!playground) return;
  setBusy(true);
  try {
    await playground.transition(before, snapshot(), action, $("animate").checked);
  } catch (error) {
    useTextView(error);
  } finally {
    setBusy(false);
  }
}

function cells(tokens, size, color, activeOffset = -1) {
  return `<div class="cells" style="--request-color:${color}">${Array.from(
    { length: size },
    (_, i) =>
      `<span class="cell ${tokens[i] === undefined ? "empty" : ""} ${i === activeOffset ? "selected" : ""}">${tokens[i] ?? "·"}</span>`,
  ).join("")}</div>`;
}
function render() {
  const r = model.requests.get(selected);
  if (r) token = Math.min(token, Math.max(0, r.length - 1));
  const address = r?.length ? model.lookup(selected, token) : null;
  $("requests").innerHTML = [...model.requests.keys()]
    .map(
      (id) =>
        `<button data-request="${id}" class="${id === selected ? "active" : ""}" style="--request-color:${colors[id]}" aria-pressed="${id === selected}">${id}</button>`,
    )
    .join("");
  $("request-length").textContent = r
    ? `${r.length} tokens · request ${selected}`
    : "No active requests. Reset to begin again.";
  $("logical-count").textContent = r ? `${r.table.length} BLOCKS` : "0 BLOCKS";
  $("logical-blocks").innerHTML = r
    ? r.table
        .map((p, b) => {
          const entries = model.pool[p].tokens.map(
            (_, i) => b * model.blockSize + i,
          );
          return `<div class="logical-block"><span>L${b}</span>${cells(entries, model.blockSize, colors[selected], address?.logical === b ? address.offset : -1)}</div>`;
        })
        .join("")
    : '<p class="quiet">All requests finished.</p>';
  $("block-table").innerHTML = r
    ? r.table
        .map(
          (p, b) =>
            `<button class="table-row ${address?.logical === b ? "active" : ""}" data-logical="${b}" aria-label="Inspect logical block ${b}, physical block ${p}">${b}<span>→</span>${p}</button>`,
        )
        .join("")
    : "";
  $("physical-blocks").innerHTML = model.pool
    .map((p, i) => {
      const owners = model.owners(i),
        color = p.refs > 1 ? "#ffff80" : (colors[owners[0]] ?? "#354257");
      return `<div class="physical-block ${p.refs ? "allocated" : ""} ${address?.physical === i ? "selected" : ""}" style="--request-color:${color}" aria-label="Physical block ${i}, ${p.refs ? `owners ${owners.join(", ")}, reference count ${p.refs}` : "free"}"><div class="block-label"><span>P${i}</span><small>${p.refs ? `${owners.join("/")} · ${p.refs}` : "free"}</small></div>${cells(
        p.tokens.map((t) => t.replace(/^[A-D]/, "")),
        model.blockSize,
        color,
        address?.physical === i ? address.offset : -1,
      )}</div>`;
    })
    .join("");
  $("token").max = Math.max(0, (r?.length ?? 1) - 1);
  $("token").value = token;
  $("token").disabled = !r?.length;
  $("token-value").value = r?.length ? token : "—";
  $("address").innerHTML = address
    ? `token <strong>${token}</strong> → b = <strong>${token} // ${model.blockSize} = ${address.logical}</strong> → table[${address.logical}] = <strong>${address.physical}</strong> → <strong>P${address.physical}[${address.offset}]</strong>`
    : "No token selected. Reset the playground to start again.";
  const stats = model.stats();
  $("metric-used").textContent = stats.used;
  $("metric-blocks").textContent = `${stats.blocks} / 12`;
  $("metric-slack").textContent = stats.slack;
  $("metric-shared").textContent = stats.shared;
  for (const action of ["append", "fork", "release"]) $(action).disabled = !r;
  $("fork").disabled = !r || model.requests.size >= 4;
  $("trace").disabled = !r?.length || !playground;
  if (busy) setBusy(true);
}
async function act(callback, action) {
  if (busy) return;
  const before = snapshot();
  try {
    $("event").textContent = callback();
  } catch (error) {
    $("event").textContent = error.message;
    render();
    return;
  }
  render();
  await updateScene(before, action);
}
$("requests").addEventListener("click", (e) => {
  const button = e.target.closest("[data-request]");
  if (button && !busy) {
    selected = button.dataset.request;
    token = 0;
    render();
    playground?.draw(snapshot());
  }
});
$("block-table").addEventListener("click", (e) => {
  const button = e.target.closest("[data-logical]");
  if (button && !busy) {
    token = Number(button.dataset.logical) * model.blockSize;
    render();
    playground?.draw(snapshot());
  }
});
$("token").addEventListener("input", (e) => {
  if (busy) return;
  token = Number(e.target.value);
  render();
  playground?.draw(snapshot());
});
$("append").addEventListener("click", () =>
  act(() => {
    const event = model.append(selected);
    token = model.get(selected).length - 1;
    return event;
  }, "append"),
);
$("fork").addEventListener("click", () =>
  act(() => {
    const source = selected,
      next = model.fork(source);
    selected = next;
    return `Forked ${source} → ${next}. Both share ${model.get(next).table.length} blocks. Append to see copy-on-write.`;
  }, "fork"),
);
$("release").addEventListener("click", () =>
  act(() => {
    const old = selected,
      freed = model.release(old);
    selected = model.requests.keys().next().value;
    token = 0;
    return `Finished ${old}. Released ${freed} physical block${freed === 1 ? "" : "s"}; blocks referenced by other requests stay allocated.`;
  }, "release"),
);
function reset() {
  if (busy) return;
  model = new Allocator(Number($("block-size").value));
  selected = "A";
  token = 0;
  $("event").textContent =
    "Reset. A has six tokens; B has three. Append to A, or fork it to share the prefix.";
  render();
  playground?.draw(snapshot());
}
$("reset").addEventListener("click", reset);
$("block-size").addEventListener("change", reset);
render();
$("trace").addEventListener("click", () => { if (!busy) void updateScene(snapshot(), "lookup"); });

async function initializePlayground() {
  try {
    const [{ PagedAttentionPlayground }] = await Promise.all([
      import("./assets/playground/scene.js?v=3"),
      document.fonts.load('24px "CMU Serif"'),
      document.fonts.load('24px "JetBrains Mono"'),
    ]);
    $("manim-stage").replaceChildren();
    playground = new PagedAttentionPlayground($("manim-stage"), {
      onToken(value) {
        if (busy) return;
        token = value;
        render();
        playground.draw(snapshot());
      },
      onPhase(text) { $("motion-caption").textContent = text; },
    });
    playground.draw(snapshot());
    $("motion-caption").textContent = "Click a token or block-table entry to inspect its address.";
    $("manim-stage").querySelector("canvas").addEventListener("webglcontextlost", () => {
      useTextView(new Error("WebGL context lost"));
      render();
    }, { once: true });
    render();
  } catch (error) {
    useTextView(error);
  }
}
void initializePlayground();

const video = $("film-player");
const shortTitles = [
  "A growing KV cache",
  "The cost of reservation",
  "Logical → physical",
  "The attention is unchanged",
  "Allocate, grow, release",
  "Share, then copy on write",
];
const clock = (t) =>
  `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
function seek(start) {
  video.currentTime = start;
  video.play().catch(() => {});
}
try {
  const [chapterResponse, transcriptResponse] = await Promise.all([
    fetch("assets/chapters.json?v=5"),
    fetch("assets/transcript.json?v=5"),
  ]);
  if (!chapterResponse.ok || !transcriptResponse.ok)
    throw new Error("Chapter metadata unavailable");
  const chapters = await chapterResponse.json(),
    cues = await transcriptResponse.json();
  $("chapter-list").innerHTML = chapters
    .map(
      (c, i) =>
        `<button class="chapter ${i === 0 ? "active" : ""}" data-start="${c.start}" aria-label="Play chapter ${i + 1}: ${c.title}"><span class="number">0${i + 1}</span><span class="chapter-title">${shortTitles[i]}</span><time>${clock(c.start)}</time></button>`,
    )
    .join("");
  $("duration").textContent = clock(
    chapters.at(-1).start + chapters.at(-1).duration,
  );
  $("chapter-list").addEventListener("click", (e) => {
    const button = e.target.closest("[data-start]");
    if (button) seek(Number(button.dataset.start));
  });
  video.addEventListener("timeupdate", () => {
    const index = chapters.findLastIndex(
      (c) => c.start <= video.currentTime + 0.05,
    );
    document.querySelectorAll(".chapter").forEach((b, i) => {
      b.classList.toggle("active", i === index);
      if (i === index) b.setAttribute("aria-current", "true");
      else b.removeAttribute("aria-current");
    });
  });
  $("transcript-content").innerHTML = chapters
    .map(
      (c, i) =>
        `<h3>${i + 1}. ${c.title}</h3>${cues
          .filter((q) => q.start >= c.start && q.start < c.start + c.duration)
          .map(
            (q) =>
              `<p><button data-seek="${q.start}" aria-label="Play from ${clock(q.start)}">${clock(q.start)}</button>${q.text}</p>`,
          )
          .join("")}`,
    )
    .join("");
  $("transcript-content").addEventListener("click", (e) => {
    const button = e.target.closest("[data-seek]");
    if (button) {
      seek(Number(button.dataset.seek));
      video.scrollIntoView({
        block: "center",
        behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
    }
  });
} catch (error) {
  $("chapter-list").innerHTML =
    '<p class="quiet">Use the video controls to explore the film.</p>';
}
