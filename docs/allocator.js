/** A deterministic, bounded KV pool with reference-counted copy-on-write. */
export class Allocator {
  constructor(blockSize = 4) {
    if (![4, 8].includes(blockSize)) throw new Error("Unsupported block size");
    this.blockSize = blockSize;
    this.pool = Array.from({ length: 12 }, () => ({ tokens: [], refs: 0 }));
    this.order = [7, 2, 10, 5, 0, 8, 3, 11, 6, 1, 9, 4];
    this.requests = new Map();
    this.add("A");
    for (let i = 0; i < 6; i++) this.append("A");
    this.add("B");
    for (let i = 0; i < 3; i++) this.append("B");
  }
  add(id) {
    if (this.requests.has(id)) throw new Error("Request already exists");
    this.requests.set(id, { length: 0, table: [] });
  }
  get(id) {
    const request = this.requests.get(id);
    if (!request) throw new Error("Select an active request");
    return request;
  }
  freeBlock() {
    const index = this.order.find((i) => this.pool[i].refs === 0);
    if (index === undefined)
      throw new Error("The pool is full. Finish a request to release blocks.");
    return index;
  }
  append(id) {
    const r = this.get(id),
      t = r.length,
      offset = t % this.blockSize;
    let p, event;
    if (offset === 0) {
      p = this.freeBlock(); // Check capacity before any mutation.
      this.pool[p] = { tokens: [], refs: 1 };
      r.table.push(p);
      event = `Token ${t}: allocated P${p}; added logical block ${r.table.length - 1}.`;
    } else {
      p = r.table.at(-1);
      if (this.pool[p].refs > 1) {
        const old = p;
        p = this.freeBlock();
        this.pool[p] = { tokens: [...this.pool[old].tokens], refs: 1 };
        this.pool[old].refs--;
        r.table[r.table.length - 1] = p;
        event = `Copy-on-write: copied P${old} → P${p}, then wrote token ${t}. Other requests keep P${old}.`;
      } else
        event = `Token ${t}: filled P${p}[${offset}]. No new block needed.`;
    }
    this.pool[p].tokens.push(`${id}${t}`);
    r.length++;
    return event;
  }
  fork(id) {
    const source = this.get(id);
    const newId = ["A", "B", "C", "D"].find(
      (candidate) => !this.requests.has(candidate),
    );
    if (!newId)
      throw new Error(
        "This demo supports four requests. Finish one before forking.",
      );
    this.requests.set(newId, {
      length: source.length,
      table: [...source.table],
    });
    for (const p of source.table) this.pool[p].refs++;
    return newId;
  }
  release(id) {
    const r = this.get(id);
    let freed = 0;
    for (const p of r.table) {
      if (--this.pool[p].refs === 0) {
        this.pool[p].tokens = [];
        freed++;
      }
    }
    this.requests.delete(id);
    return freed;
  }
  lookup(id, token) {
    const r = this.get(id);
    if (!Number.isInteger(token) || token < 0 || token >= r.length)
      throw new Error("Token out of range");
    const logical = Math.floor(token / this.blockSize),
      offset = token % this.blockSize;
    return { logical, physical: r.table[logical], offset };
  }
  owners(physical) {
    return [...this.requests]
      .filter(([, r]) => r.table.includes(physical))
      .map(([id]) => id);
  }
  stats() {
    const allocated = this.pool.filter((p) => p.refs > 0);
    const used = allocated.reduce((sum, p) => sum + p.tokens.length, 0);
    return {
      blocks: allocated.length,
      used,
      slack: allocated.length * this.blockSize - used,
      shared: allocated.filter((p) => p.refs > 1).length,
    };
  }
}
