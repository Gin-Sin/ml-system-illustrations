import { build } from "esbuild";
import { mkdir, writeFile, readFile, readdir, rm } from "node:fs/promises";

await mkdir("docs/assets/playground", { recursive: true });
for (const file of await readdir("docs/assets/playground")) {
  if (file.endsWith(".js")) await rm(`docs/assets/playground/${file}`);
}
const result = await build({
  entryPoints: ["web/playground.js"], outdir: "docs/assets/playground",
  entryNames: "scene", chunkNames: "[name]-[hash]", bundle: true,
  format: "esm", splitting: true, minify: true, target: "es2022",
  // Keep embedded third-party shader strings escaped in generated source.
  supported: { "template-literal": false },
  legalComments: "eof", logLevel: "info", metafile: true,
});
const licenses = [];
const packages = new Set(Object.keys(result.metafile.inputs).flatMap(path => {
  const match = path.match(/^(node_modules\/(?:@[^/]+\/)?[^/]+)\//);
  return match ? [match[1]] : [];
}));
// manim-web's distribution already embeds its renderer/math dependencies,
// so their files do not all appear as separate esbuild inputs.
for (const name of [
  "three", "earcut", "katex", "opentype.js", "polygon-clipping", "splaytree", "robust-predicates",
  "@mathjax/src", "@mathjax/mathjax-newcm-font", "mhchemparser", "speech-rule-engine", "wicked-good-xpath",
]) packages.add(`node_modules/${name}`);
for (const directory of [...packages].sort()) {
  const { name, version } = JSON.parse(await readFile(`${directory}/package.json`, "utf8"));
  const file = (await readdir(directory)).find(file => /^licen[cs]e(?:$|\.)/i.test(file));
  const licensePath = file ? `${directory}/${file}`
    : name === "@mathjax/mathjax-newcm-font" ? "node_modules/@mathjax/src/LICENSE"
    : name === "splaytree" ? `${directory}/Readme.md` : null;
  if (!licensePath) throw new Error(`Missing redistribution license for ${name}`);
  const contents = await readFile(licensePath, "utf8");
  licenses.push(`${name} ${version}\n${name === "splaytree" ? contents.split("## License")[1].trim() : contents}`);
}
await writeFile("docs/assets/playground/LICENSES.txt", licenses.join("\n\n").replace(/[\t ]+$/gm, ""));
