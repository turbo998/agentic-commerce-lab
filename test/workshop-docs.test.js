import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createAppServer } from "../src/server.js";

const workshop = new URL("../docs/workshops/copilot-hve-commerce/", import.meta.url);
const read = (name) => readFileSync(new URL(name, workshop), "utf8");

test("outline has 24 contiguous units covering exactly 60 minutes including Q&A", () => {
  const ranges = [...read("outline.md").matchAll(/^## \d+\. .+[（(](\d\d):(\d\d)–(\d\d):(\d\d)[）)]\r?$/gm)]
    .map(([, sm, ss, em, es]) => [Number(sm) * 60 + Number(ss), Number(em) * 60 + Number(es)]);
  assert.equal(ranges.length, 24);
  assert.equal(ranges[0][0], 0);
  assert.equal(ranges.at(-1)[1], 3600);
  ranges.forEach(([start, end], i) => {
    assert.ok(end > start);
    if (i) assert.equal(start, ranges[i - 1][1]);
  });
});

test("all 26 report sources and all 15 questions map to explicit evidence and host boundaries", () => {
  const register = JSON.parse(read("sources.json"));
  const ids = new Map(register.sources.map((source) => [source.id, source]));
  assert.equal(ids.size, register.sources.length);
  assert.equal(Object.keys(register.reportSourceMapping).length, 26);
  const html = readFileSync(new URL("../public/hve-report.html", import.meta.url), "utf8");
  const js = readFileSync(new URL("../public/hve-report.js", import.meta.url), "utf8");
  const used = new Set([...html.matchAll(/data-source="([^"]+)"/g)].map(([, key]) => key));
  for (const key of used) {
    const source = ids.get(register.reportSourceMapping[key]);
    assert.ok(source?.url && source.evidenceType && source.verification && source.applicableHost, key);
    assert.ok(js.includes(`"${key}":`), key);
  }
  assert.deepEqual(register.questionCoverage.map((entry) => entry.question), Array.from({ length: 15 }, (_, i) => i + 1));
  for (const question of register.questionCoverage) {
    assert.ok(question.sources.length);
    question.sources.forEach((id) => assert.ok(ids.has(id), `${question.question}:${id}`));
  }
  for (const source of register.sources) {
    if (source.path) assert.ok(existsSync(new URL(source.path, workshop)), source.path);
    if (source.url?.includes("github.com/microsoft/hve-core/blob/")) assert.ok(source.url.includes(register.hveRevision));
  }
  assert.equal((html.match(/<article id=/g) ?? []).length, 16);
  assert.equal((html.match(/<script[^>]+src=/g) ?? []).length, 2);
  assert.doesNotMatch(html, /<script>([\s\S]*?)<\/script>|<style>|style="/);
  assert.ok(html.includes('<ol id="toc"><li>'), "TOC readable without JavaScript");
  assert.ok(html.includes('data-source="readme" href="https:'), "References readable without JavaScript");
});

test("only reviewed workshop files are locally readable; application/tracking/state stay unavailable", async () => {
  const dir = mkdtempSync(join(tmpdir(), "commerce-docs-"));
  const server = createAppServer({ statePath: join(dir, "state.json") });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    for (const path of [
      "/hve-report.html", "/hve-report.css", "/hve-theme.js", "/hve-report.js",
      "/workshop/outline.md", "/workshop/demo-runbook.md", "/workshop/sources.json",
      "/workshop/evidence/host.json", "/workshop/evidence/rpi-execution.md",
      "/workshop/evidence/browser-commerce.json", "/workshop/evidence/browser-report.json",
    ]) {
      const response = await fetch(`${base}${path}`);
      assert.equal(response.status, 200, path);
      assert.doesNotMatch(response.headers.get("content-security-policy"), /unsafe-inline/);
    }
    for (const path of [
      "/workshop/../../src/agent.js", "/workshop/.copilot-tracking/plans/private.md",
      "/workshop/evidence/../host.json", "/workshop/data/state.json", "/workshop/sources.md",
    ]) {
      assert.equal((await fetch(`${base}${path}`)).status, 404, path);
    }
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
    rmSync(dir, { recursive: true, force: true });
  }
});
