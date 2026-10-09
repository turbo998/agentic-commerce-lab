import { createServer as httpServer } from "node:http";
import { mkdirSync, readFileSync, renameSync, writeFileSync, existsSync } from "node:fs";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { proposeTask, requestTaskAction, offlinePlanner } from "./agent.js";
import { paymentRequired } from "./protocol.js";
import {
  AuthorityError,
  applyPaymentEvent,
  createPayment,
  createTaskConsent,
  deliverPaidResource,
  fulfillPayment,
  initialState,
  reconcilePayment,
  recordFulfillmentFailure,
  refundPayment,
  revokeConsent,
  resolveFulfillment,
  snapshot,
} from "./authority.js";

const root = dirname(fileURLToPath(import.meta.url));
const staticRoot = resolve(root, "..", "public");
const defaultStatePath = resolve(root, "..", "data", "state.json");
const MIME = { ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8" };

function readState(path) {
  if (!existsSync(path)) return initialState();
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`Cannot read simulation state at ${path}: ${error.message}`);
  }
}

function persist(path, state) {
  mkdirSync(dirname(path), { recursive: true });
  const temporary = `${path}.${process.pid}.tmp`;
  writeFileSync(temporary, JSON.stringify(state, null, 2), { mode: 0o600 });
  renameSync(temporary, path);
}

async function readBody(request) {
  let raw = "";
  for await (const chunk of request) {
    raw += chunk;
    if (raw.length > 64_000) throw new AuthorityError("BODY_TOO_LARGE", "请求超过大小限制。");
  }
  let value;
  try {
    value = raw ? JSON.parse(raw) : {};
  } catch {
    throw new AuthorityError("INVALID_JSON", "请求必须是有效 JSON。");
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new AuthorityError("INVALID_BODY", "请求正文必须是 JSON 对象。");
  }
  return value;
}

function mutationError(request) {
  const origin = request.headers.origin;
  if (origin) {
    try {
      if (new URL(origin).host !== request.headers.host) {
        return { status: 403, error: "CROSS_ORIGIN", message: "仅允许同源本地操作。" };
      }
    } catch {
      return { status: 403, error: "CROSS_ORIGIN", message: "Origin 标头无效。" };
    }
  }
  if (!request.headers["content-type"]?.toLowerCase().startsWith("application/json")) {
    return { status: 415, error: "JSON_REQUIRED", message: "状态变更只接受 JSON 请求。" };
  }
  return null;
}

function json(response, status, value) {
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
  });
  response.end(JSON.stringify(value));
}

function createHandler(statePath, planner = offlinePlanner) {
  let state = readState(statePath);
  const commit = (operation) => {
    const next = JSON.parse(JSON.stringify(state));
    const result = operation(next);
    persist(statePath, next);
    state = next;
    return result;
  };

  return async (request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    if (request.method === "GET" && url.pathname === "/api/state") return json(response, 200, snapshot(state));
    if (request.method === "POST" && url.pathname === "/api/reset") {
      const rejected = mutationError(request);
      if (rejected) return json(response, rejected.status, rejected);
      try {
        await readBody(request);
      } catch (error) {
        if (error instanceof AuthorityError) return json(response, 400, { error: error.code, message: error.message });
        throw error;
      }
      const next = initialState();
      persist(statePath, next);
      state = next;
      return json(response, 200, snapshot(state));
    }
    if (url.pathname.startsWith("/api/")) {
      const taskLookup = url.pathname.match(/^\/api\/tasks\/([^/]+)$/);
      if (request.method === "GET" && taskLookup) {
        const task = state.tasks[taskLookup[1]];
        if (!task || task.ownerId !== url.searchParams.get("ownerId")) {
          return json(response, 404, { error: "TASK_NOT_FOUND" });
        }
        return json(response, 200, task);
      }
      if (request.method !== "POST") return json(response, 405, { error: "METHOD_NOT_ALLOWED" });
      const rejected = mutationError(request);
      if (rejected) return json(response, rejected.status, rejected);
      try {
        const input = await readBody(request);
        let result;
        const taskAction = url.pathname.match(/^\/api\/tasks\/([^/]+)\/actions$/);
        if (url.pathname === "/api/tasks" && request.method === "POST") {
          const task = await proposeTask(input, planner);
          result = commit((next) => {
            next.tasks[task.id] = task;
            next.events.push({
              id: `evt-${next.sequence++}`,
              type: "agent.task_proposed",
              paymentId: null,
              taskId: task.id,
              at: new Date().toISOString(),
            });
            return task;
          });
          return json(response, 201, { result, state: snapshot(state) });
        }
        if (taskAction) {
          result = commit((next) => requestTaskAction(next, {
            ...input,
            taskId: taskAction[1],
          }));
          return json(response, 200, { result, state: snapshot(state) });
        }
        const resourceRoute = url.pathname.match(/^\/api\/resources\/([^/]+)$/);
        if (resourceRoute) {
          if (!input.consentId) {
            const challenge = paymentRequired(resourceRoute[1]);
            return json(response, challenge.status, challenge);
          }
          result = commit((next) => {
            const consent = next.consents[input.consentId];
            if (!consent || consent.quoteId !== resourceRoute[1]) {
              throw new AuthorityError("RESOURCE_CONSENT_REQUIRED", "此资源需要匹配的用户授权。");
            }
            const payment = createPayment(next, {
              ownerId: input.ownerId,
              taskId: input.taskId,
              consentId: input.consentId,
              idempotencyKey: input.idempotencyKey,
            });
            const delivery = deliverPaidResource(next, {
              ownerId: input.ownerId,
              paymentId: payment.id,
            });
            return { payment, delivery };
          });
          return json(response, 200, { result, state: snapshot(state) });
        }
        switch (url.pathname) {
          case "/api/consents":
            result = commit((next) => createTaskConsent(next, input));
            break;
          case "/api/consents/revoke":
            result = commit((next) => revokeConsent(next, input));
            break;
          case "/api/payments":
            result = commit((next) => createPayment(next, input));
            break;
          case "/api/payments/reconcile":
            result = commit((next) => reconcilePayment(next, input));
            break;
          case "/api/payments/fulfill":
            result = commit((next) => fulfillPayment(next, input));
            break;
          case "/api/payments/fulfillment/fail":
            result = commit((next) => recordFulfillmentFailure(next, input));
            break;
          case "/api/payments/fulfillment/resolve":
            result = commit((next) => resolveFulfillment(next, input));
            break;
          case "/api/payments/refund":
            result = commit((next) => refundPayment(next, input));
            break;
          case "/api/payments/events":
            result = commit((next) => applyPaymentEvent(next, input));
            break;
          default:
            return json(response, 404, { error: "NOT_FOUND" });
        }
        return json(response, 200, { result, state: snapshot(state) });
      } catch (error) {
        if (error instanceof AuthorityError) return json(response, 400, { error: error.code, message: error.message });
        throw error;
      }
    }

    if (request.method !== "GET") return json(response, 405, { error: "METHOD_NOT_ALLOWED" });
    if (url.pathname.startsWith("/api/resources/")) return json(response, 405, { error: "METHOD_NOT_ALLOWED" });
    const requested = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
    const path = resolve(staticRoot, requested);
    if (!path.startsWith(staticRoot + sep)) return json(response, 404, { error: "NOT_FOUND" });
    try {
      const content = readFileSync(path);
      response.writeHead(200, {
        "content-type": MIME[extname(path)] ?? "application/octet-stream",
        "cache-control": "no-store",
        "content-security-policy": "default-src 'self'; connect-src 'self'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'",
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
      });
      return response.end(content);
    } catch (error) {
      if (error.code === "ENOENT" || error.code === "EISDIR") return json(response, 404, { error: "NOT_FOUND" });
      throw error;
    }
  };
}

export function createAppServer({ statePath = defaultStatePath, planner = offlinePlanner } = {}) {
  const handler = createHandler(statePath, planner);
  return httpServer((request, response) => {
    handler(request, response).catch((error) => {
      console.error("Request failed:", error);
      if (!response.headersSent) json(response, 500, { error: "INTERNAL_ERROR" });
      else response.destroy(error);
    });
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT ?? 4173);
  const server = createAppServer();
  server.listen(port, "127.0.0.1", () => {
    console.log(`SIMULATED / OFFLINE demo: http://127.0.0.1:${port}`);
  });
}
