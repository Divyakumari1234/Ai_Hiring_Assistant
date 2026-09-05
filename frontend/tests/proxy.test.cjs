const assert = require("node:assert/strict");
const { test } = require("node:test");
const { registerHooks } = require("node:module");
const { NextRequest } = require("next/server");
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    return nextResolve(specifier === "next/server" ? "next/server.js" : specifier, context);
  },
});
const { proxy } = require("../proxy.ts");
hooks.deregister();

test("hosted workspace and API require reviewer authentication", (t) => {
  const oldPassword = process.env.REVIEW_PASSWORD;
  const oldUsername = process.env.REVIEW_USERNAME;
  t.after(() => {
    if (oldPassword === undefined) delete process.env.REVIEW_PASSWORD;
    else process.env.REVIEW_PASSWORD = oldPassword;
    if (oldUsername === undefined) delete process.env.REVIEW_USERNAME;
    else process.env.REVIEW_USERNAME = oldUsername;
  });
  process.env.REVIEW_PASSWORD = "test-only-password";
  process.env.REVIEW_USERNAME = "reviewer";
  for (const route of ["/", "/api/dashboard", "/api/outreach"]) {
    assert.equal(proxy(new NextRequest(`https://example.test${route}`)).status, 401);
  }
  const headers = { authorization: "Basic " + Buffer.from("reviewer:test-only-password").toString("base64") };
  assert.equal(proxy(new NextRequest("https://example.test/api/dashboard", { headers })).status, 200);
  assert.equal(proxy(new NextRequest("https://example.test/healthz")).status, 200);
  assert.equal(proxy(new NextRequest("https://example.test/", {headers: {authorization: "Basic invalid"}})).status, 401);
});
