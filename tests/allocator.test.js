import test from "node:test";
import assert from "node:assert/strict";
import { Allocator } from "../docs/allocator.js";

function validate(model) {
  const refs = Array(12).fill(0);
  for (const [id, r] of model.requests) {
    assert.equal(r.table.length, Math.ceil(r.length / model.blockSize));
    assert.equal(new Set(r.table).size, r.table.length);
    r.table.forEach((p, b) => {
      refs[p]++;
      assert.equal(
        model.pool[p].tokens.length,
        Math.min(model.blockSize, r.length - b * model.blockSize),
      );
    });
    for (let t = 0; t < r.length; t++) {
      const { physical, offset } = model.lookup(id, t);
      assert.ok(model.pool[physical].tokens[offset]);
    }
  }
  model.pool.forEach((p, i) => {
    assert.equal(p.refs, refs[i]);
    assert.ok(p.tokens.length <= model.blockSize);
    if (!p.refs) assert.deepEqual(p.tokens, []);
  });
  const stats = model.stats();
  assert.equal(stats.used + stats.slack, stats.blocks * model.blockSize);
}

test("lookup crosses logical blocks without assuming physical adjacency", () => {
  const m = new Allocator();
  assert.deepEqual(m.get("A").table, [7, 2]);
  assert.deepEqual(m.lookup("A", 5), { logical: 1, physical: 2, offset: 1 });
  m.append("A");
  m.append("A");
  m.append("A");
  assert.deepEqual(m.get("A").table, [7, 2, 5]);
  assert.deepEqual(m.lookup("A", 8), { logical: 2, physical: 5, offset: 0 });
  assert.throws(() => m.lookup("A", 9), /out of range/);
  validate(m);
});
test("fork shares pages, partial-page writes preserve sibling data", () => {
  const m = new Allocator();
  const snapshot = [...m.pool[2].tokens];
  const c = m.fork("A");
  assert.equal(c, "C");
  assert.equal(m.stats().blocks, 3);
  assert.equal(m.stats().shared, 2);
  assert.match(m.append(c), /Copy-on-write/);
  assert.deepEqual(m.get("A").table, [7, 2]);
  assert.deepEqual(m.get(c).table, [7, 5]);
  assert.deepEqual(m.pool[2].tokens, snapshot);
  assert.deepEqual(m.pool[5].tokens, [...snapshot, "C6"]);
  assert.equal(m.pool[7].refs, 2);
  assert.equal(m.pool[2].refs, 1);
  validate(m);
});
test("full shared blocks stay shared when a continuation allocates its next page", () => {
  const m = new Allocator();
  m.append("A");
  m.append("A");
  const c = m.fork("A");
  assert.match(m.append(c), /allocated/);
  assert.deepEqual(m.get(c).table.slice(0, 2), m.get("A").table);
  assert.equal(m.pool[2].refs, 2);
  validate(m);
});
test("release frees only blocks whose final owner finishes; empty pool is reusable", () => {
  const m = new Allocator();
  const c = m.fork("A");
  assert.equal(m.release("A"), 0);
  assert.equal(m.release(c), 2);
  assert.equal(m.release("B"), 1);
  assert.deepEqual(m.stats(), { blocks: 0, used: 0, slack: 0, shared: 0 });
  m.add("A");
  m.append("A");
  assert.equal(m.get("A").table[0], 7);
  validate(m);
});
test("out-of-memory during copy-on-write is atomic", () => {
  const m = new Allocator();
  m.fork("A");
  while (m.stats().blocks < 12) m.append("B");
  const snapshot = JSON.stringify({ pool: m.pool, requests: [...m.requests] });
  assert.throws(() => m.append("C"), /pool is full/);
  assert.equal(
    JSON.stringify({ pool: m.pool, requests: [...m.requests] }),
    snapshot,
  );
  validate(m);
});
test("mixed operations preserve references, capacity, and lookup at both block sizes", () => {
  let seed = 42;
  const random = () =>
    (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32;
  for (const size of [4, 8]) {
    const m = new Allocator(size);
    for (let i = 0; i < 1200; i++) {
      if (!m.requests.size) m.add("A");
      const ids = [...m.requests.keys()],
        id = ids[Math.floor(random() * ids.length)],
        op = random();
      try {
        if (op < 0.68) m.append(id);
        else if (op < 0.84) m.fork(id);
        else m.release(id);
      } catch (error) {
        assert.match(error.message, /pool is full|four requests/);
      }
      validate(m);
    }
  }
});
