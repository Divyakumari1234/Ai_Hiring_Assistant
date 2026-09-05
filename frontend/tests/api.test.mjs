import assert from "node:assert/strict";
import { test } from "node:test";
import { api } from "../src/api.ts";

test("read requests recover from a temporary proxy failure", async (t) => {
  let count = 0;
  t.mock.method(globalThis, "fetch", async () => {
    count++;
    return count === 1
      ? new Response("Bad Gateway", { status: 502 })
      : Response.json({ source: "hunar", calls: [] });
  });
  assert.equal((await api.dashboard()).source, "hunar");
  assert.equal(count, 2);
});

test("read retries stop and report the server error", async (t) => {
  let count = 0;
  t.mock.method(globalThis, "fetch", async () => {
    count++;
    return new Response("Bad Gateway", { status: 502 });
  });
  await assert.rejects(api.dashboard(), /HTTP 502/);
  assert.equal(count, 3);
});

test("live call requests are never retried after a network failure", async (t) => {
  let count = 0;
  t.mock.method(globalThis, "fetch", async () => {
    count++;
    throw new TypeError("Network failure");
  });
  await assert.rejects(api.outreach(["test-contact"], "test-agent", true), /avoid duplicate calls/);
  assert.equal(count, 1);
});

test("live call requests are never retried after a gateway error", async (t) => {
  let count = 0;
  t.mock.method(globalThis, "fetch", async () => {
    count++;
    return new Response("Bad Gateway", { status: 502 });
  });
  await assert.rejects(api.outreach(["test-contact"], "test-agent", true));
  assert.equal(count, 1);
});

test("authorization failures are reported without retrying", async (t) => {
  let count = 0;
  t.mock.method(globalThis, "fetch", async () => {
    count++;
    return Response.json({ detail: "Access denied" }, { status: 401 });
  });
  await assert.rejects(api.dashboard(), /Access denied/);
  assert.equal(count, 1);
});
