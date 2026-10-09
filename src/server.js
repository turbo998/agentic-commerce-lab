import { createServer as httpServer } from "node:http";
import { mkdirSync, readFileSync, renameSync, writeFileSync, existsSync } from "node:fs";
import { dirname, extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { proposeTask, requestTaskAction, offlinePlanner } from "./agent.js";
import { paymentRequired } from "./protocol.js";
import { CATALOG } from "./catalog.js";
import {
  AuthorityError,
  applyPaymentEvent,
  approveConsentRequest,
  approveRefundRequest,
  createPayment,
  createResourceChallenge,
  createTaskConsent,
  denyConsentRequest,
  deliverPaidResource,
  executeConsent,
  fulfillPayment,
  initialState,
  reconcilePayment,
  recordFulfillmentFailure,
  refundPayment,
  resetTenantState,
  revokeConsent,
  requestRefund,
  resolveFulfillment,
  snapshot,
} from "./authority.js";
import { createIdentityRegistry, assertIdentityRole, assertNoClientIdentity } from "./identity.js";

const root = dirname(fileURLToPath(import.meta.url));
const staticRoot = resolve(root, "..", "public");
const defaultStatePath = resolve(root, "..", "data", "state.json");
const MIME = { ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8" };

function readState(path) {
  if (!existsSync(path)) return initialState();
  try {
    const loaded = JSON.parse(readFileSync(path, "utf8"));
    const current = initialState();
    for (const key of Object.keys(current)) {
      if (loaded[key] === undefined) loaded[key] = current[key];
    }
    for (const section of ["consents", "consentRequests", "tasks", "payments", "refundRequests"]) {
      for (const record of Object.values(loaded[section])) {
        if (record.ownerId === "user-demo") record.ownerId = "alex";
        if (!record.tenantId) record.tenantId = "tenant-demo";
      }
    }
    const taskIds = new Set([
      ...Object.values(loaded.tasks).map((task) => task.id),
      ...Object.values(loaded.payments).map((payment) => payment.taskId),
      ...Object.values(loaded.consents).map((consent) => consent.taskId),
    ].filter(Boolean));
    for (const taskId of taskIds) {
      const associated = [
        ...Object.values(loaded.payments).filter((payment) => payment.taskId === taskId),
        ...Object.values(loaded.consents).filter((consent) => consent.taskId === taskId),
      ];
      const ownerId = associated[0]?.ownerId ?? "alex";
      const tenantId = associated[0]?.tenantId ?? "tenant-demo";
      const record = loaded.tasks[taskId] ?? {
        id: taskId,
        ownerId,
        tenantId,
        journey: "weekend",
        goal: "Migrated local simulation task",
        status: "migrated",
        suggestions: [],
        createdAt: 0,
        actionRequests: {},
      };
      if (!record.budgetLimit) {
        const quoteCurrency = associated[0]?.currency ?? "USD";
        const committedMinor = associated
          .filter((item) => item.currency === quoteCurrency && item.status !== "declined")
          .reduce((total, item) => total + item.amountMinor, 0);
        record.budgetLimit = {
          currency: quoteCurrency,
          amountMinor: Math.max(committedMinor, CATALOG[associated[0]?.quoteId]?.amountMinor ?? 1),
        };
      }
      record.ownerId = record.ownerId === "user-demo" ? "alex" : record.ownerId;
      record.tenantId ??= tenantId;
      loaded.tasks[taskId] = record;
    }
    return loaded;
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

function requiredRoles(method, pathname) {
  if (method === "GET") return ["agent", "human"];
  if (pathname === "/api/reset") return ["human"];
  if (pathname === "/api/payments/fulfill" || pathname.startsWith("/api/payments/fulfillment/") ||
      pathname === "/api/payments/refund" || pathname === "/api/consents/revoke" ||
      pathname === "/api/payments/events") return ["human"];
  if (pathname.startsWith("/api/commerce/v1/")) {
    if (/\/(approve|deny|revoke)$/.test(pathname)) return ["human"];
    if (pathname.includes("/fulfillment/") || pathname.endsWith("/fulfill") || pathname.endsWith("/refund")) return ["human"];
    return ["agent", "human"];
  }
  if (pathname === "/api/consents" || pathname === "/api/tasks" ||
      pathname.includes("/actions") || pathname.startsWith("/api/resources/") ||
      pathname === "/api/payments" || pathname === "/api/payments/reconcile") return ["agent", "human"];
  return null;
}

function handleCommerceApi(request, response, url, identity, state, commit, planner) {
  const apiRoot = "/api/commerce/v1";
  const path = url.pathname.slice(apiRoot.length) || "/";
  const method = request.method;
  const failResponse = (error) => {
    if (error instanceof AuthorityError) {
      const status = error.code.endsWith("_NOT_FOUND") ? 404 : 400;
      return json(response, status, { error: error.code, message: error.message });
    }
    throw error;
  };
  const respond = (status, result) => json(response, status, result);
  const visible = (record) => record && record.ownerId === identity.subject && record.tenantId === identity.tenantId;

  if (method === "GET") {
    if (path === "/catalog") {
      const journey = url.searchParams.get("journey");
      const catalog = Object.values(CATALOG).filter((quote) => !journey || quote.journey === journey);
      return respond(200, { items: catalog, currencies: ["USD", "HKD", "USDC"], mode: "SIMULATED / OFFLINE" });
    }
    if (path === "/status") return respond(200, snapshot(state, identity));
    const task = path.match(/^\/tasks\/([^/]+)$/);
    if (task) {
      const record = state.tasks[task[1]];
      return record?.ownerId === identity.subject && record?.tenantId === identity.tenantId
        ? respond(200, record)
        : respond(404, { error: "TASK_NOT_FOUND" });
    }
    const consentRequest = path.match(/^\/consent-requests\/([^/]+)$/);
    if (consentRequest) {
      const record = state.consentRequests[consentRequest[1]];
      return visible(record) ? respond(200, record) : respond(404, { error: "CONSENT_REQUEST_NOT_FOUND" });
    }
    const refundRequest = path.match(/^\/refund-requests\/([^/]+)$/);
    if (refundRequest) {
      const record = state.refundRequests[refundRequest[1]];
      return visible(record) ? respond(200, record) : respond(404, { error: "REFUND_REQUEST_NOT_FOUND" });
    }
    return respond(404, { error: "NOT_FOUND" });
  }
  if (method !== "POST") return respond(405, { error: "METHOD_NOT_ALLOWED" });

  return readBody(request).then((input) => {
    assertNoClientIdentity(input);
    if (path === "/resources/travel-guide") {
      if (!input.challengeId && !input.consentRequestId) {
        if (typeof input.taskId !== "string") {
          throw new AuthorityError("TASK_REQUIRED", "请求 HTTP 402 challenge 必须绑定所属任务。");
        }
        const challenge = commit((next) => createResourceChallenge(next, {
          ownerId: identity.subject, tenantId: identity.tenantId, taskId: input.taskId,
        }));
        return respond(402, paymentRequired("travel-guide", challenge));
      }
      const request = state.consentRequests[input.consentRequestId];
      const challenge = state.resourceChallenges[input.challengeId];
      const alreadyCompleted = request?.status === "completed" && challenge?.status === "completed";
      if (!visible(request) || !challenge || !visible(challenge) ||
          request.resourceChallengeId !== challenge.id ||
          request.id !== challenge.consentRequestId ||
          request.taskId !== challenge.taskId ||
          input.taskId !== challenge.taskId ||
          request.quoteId !== "travel-guide" ||
          (!alreadyCompleted && (request.status !== "approved" || challenge.status !== "approved" ||
            challenge.expiresAt <= Date.now()))) {
        return respond(409, { error: "RESOURCE_CONSENT_REQUIRED", message: "需要此任务对应的有效 402 challenge 和已批准 consent。" });
      }
      if (alreadyCompleted) {
        const payment = structuredClone(state.payments[challenge.paymentId]);
        const delivery = structuredClone(state.resourceDeliveries[challenge.paymentId]);
        return respond(200, { result: { challenge: structuredClone(challenge), payment, delivery }, state: snapshot(state, identity) });
      }
      const result = commit((next) => {
        const currentRequest = next.consentRequests[request.id];
        const currentChallenge = next.resourceChallenges[challenge.id];
        const execution = executeConsent(next, {
          ownerId: identity.subject,
          tenantId: identity.tenantId,
          consentId: currentRequest.consentId,
          idempotencyKey: `resource-consent-${currentChallenge.id}`,
          challengeId: currentChallenge.id,
        });
        const delivery = deliverPaidResource(next, {
          ownerId: identity.subject, tenantId: identity.tenantId, paymentId: execution.payment.id,
        });
        currentChallenge.status = "completed";
        currentChallenge.paymentId = execution.payment.id;
        currentChallenge.deliveryId = delivery.id;
        currentRequest.status = "completed";
        currentRequest.completedAt = Date.now();
        return { challenge: currentChallenge, ...execution, delivery };
      });
      return respond(200, { result, state: snapshot(state, identity) });
    }
    if (path === "/tasks") {
      return proposeTask({
        ...input,
        ownerId: identity.subject,
        tenantId: identity.tenantId,
      }, planner).then((task) => {
        const result = commit((next) => {
          next.tasks[task.id] = task;
          next.events.push({
            id: `evt-${next.sequence++}`, type: "agent.task_proposed", paymentId: null,
            taskId: task.id, at: new Date().toISOString(),
          });
          return task;
        });
        return respond(201, { result });
      });
    }
    const taskAction = path.match(/^\/tasks\/([^/]+)\/actions$/);
    if (taskAction) {
      const result = commit((next) => requestTaskAction(next, {
        ...input,
        ownerId: identity.subject,
        tenantId: identity.tenantId,
        taskId: taskAction[1],
      }));
      return respond(200, { result });
    }
    if (path === "/consent-requests") {
      const result = commit((next) => createTaskConsent(next, {
        ...input, ownerId: identity.subject, tenantId: identity.tenantId,
      }));
      return respond(201, { result });
    }
    const approveRequest = path.match(/^\/consent-requests\/([^/]+)\/(approve|deny)$/);
    if (approveRequest) {
      const result = commit((next) => approveRequest[2] === "approve"
        ? approveConsentRequest(next, {
          ownerId: identity.subject, tenantId: identity.tenantId, requestId: approveRequest[1],
        })
        : denyConsentRequest(next, {
          ownerId: identity.subject, tenantId: identity.tenantId, requestId: approveRequest[1],
        }));
      return respond(200, { result });
    }
    const execute = path.match(/^\/consents\/([^/]+)\/execute$/);
    if (execute) {
      const result = commit((next) => executeConsent(next, {
        ownerId: identity.subject,
        tenantId: identity.tenantId,
        consentId: execute[1],
        idempotencyKey: `consent-execute-${execute[1]}`,
      }));
      return respond(200, { result });
    }
    const revoke = path.match(/^\/consents\/([^/]+)\/revoke$/);
    if (revoke) {
      const result = commit((next) => revokeConsent(next, {
        ownerId: identity.subject, tenantId: identity.tenantId, consentId: revoke[1],
      }));
      return respond(200, { result });
    }
    if (path === "/refund-requests") {
      const result = commit((next) => requestRefund(next, {
        ...input, ownerId: identity.subject, tenantId: identity.tenantId,
      }));
      return respond(201, { result });
    }
    const approveRefund = path.match(/^\/refund-requests\/([^/]+)\/approve$/);
    if (approveRefund) {
      const result = commit((next) => approveRefundRequest(next, {
        ownerId: identity.subject, tenantId: identity.tenantId, requestId: approveRefund[1],
      }));
      return respond(200, { result });
    }
    const payment = path.match(/^\/payments\/([^/]+)\/(reconcile|fulfill|refund)$/);
    if (payment) {
      if (payment[2] === "reconcile") {
        const record = state.payments[payment[1]];
        if (!visible(record)) return respond(404, { error: "PAYMENT_NOT_FOUND" });
        const result = commit((next) => reconcilePayment(next, { paymentId: payment[1] }));
        return respond(200, { result });
      }
      if (payment[2] === "fulfill") {
        const result = commit((next) => fulfillPayment(next, {
          ownerId: identity.subject, tenantId: identity.tenantId, paymentId: payment[1],
        }));
        return respond(200, { result });
      }
      const result = commit((next) => refundPayment(next, {
        ...input, ownerId: identity.subject, tenantId: identity.tenantId, paymentId: payment[1],
      }));
      return respond(200, { result });
    }
    const failedFulfillment = path.match(/^\/payments\/([^/]+)\/fulfillment\/fail$/);
    if (failedFulfillment) {
      const result = commit((next) => recordFulfillmentFailure(next, {
        ...input, ownerId: identity.subject, tenantId: identity.tenantId, paymentId: failedFulfillment[1],
      }));
      return respond(200, { result });
    }
    const fulfillmentResolution = path.match(/^\/payments\/([^/]+)\/fulfillment\/resolve$/);
    if (fulfillmentResolution) {
      const result = commit((next) => resolveFulfillment(next, {
        ...input, ownerId: identity.subject, tenantId: identity.tenantId, paymentId: fulfillmentResolution[1],
      }));
      return respond(200, { result });
    }
    if (path === "/resources/travel-guide") {
      const challenge = paymentRequired("travel-guide");
      if (!input.consentRequestId) return respond(402, challenge);
      const request = state.consentRequests[input.consentRequestId];
      if (!visible(request) || request.quoteId !== "travel-guide" || request.status !== "approved") {
        return respond(409, { error: "RESOURCE_CONSENT_REQUIRED" });
      }
      const result = commit((next) => {
        const current = next.consentRequests[request.id];
        const execution = executeConsent(next, {
          ownerId: identity.subject,
          tenantId: identity.tenantId,
          consentId: current.consentId,
          idempotencyKey: `resource-consent-${current.id}`,
        });
        return { challenge, ...execution };
      });
      return respond(200, { result });
    }
    return respond(404, { error: "NOT_FOUND" });
  }).catch(failResponse);
}

function createHandler(statePath, planner = offlinePlanner, identities) {
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
    if (request.method === "POST" && url.pathname === "/api/demo/human-session") {
      const rejected = mutationError(request);
      if (rejected) return json(response, rejected.status, rejected);
      const expectedOrigin = `http://${request.headers.host}`;
      if (request.headers.origin !== expectedOrigin || request.headers["sec-fetch-site"] !== "same-origin") {
        return json(response, 403, { error: "HUMAN_SESSION_REQUIRES_LOCAL_PAGE", message: "人工演示会话只能从同源本地人工审核页面启动。" });
      }
      try {
        const input = await readBody(request);
        if (Object.keys(input).some((key) => key !== "persona")) {
          throw new AuthorityError("INVALID_DEMO_IDENTITY", "本地会话只接受固定的 persona 选择。");
        }
        return json(response, 201, identities.createHumanSession(input.persona));
      } catch (error) {
        if (error instanceof AuthorityError) {
          const status = error.code.endsWith("_NOT_FOUND") ? 404 : 400;
          return json(response, status, { error: error.code, message: error.message });
        }
        throw error;
      }
    }
    if (request.method === "POST" && url.pathname === "/api/demo/session") {
      const rejected = mutationError(request);
      if (rejected) return json(response, rejected.status, rejected);
      try {
        const input = await readBody(request);
        if (Object.keys(input).some((key) => key !== "persona")) {
          throw new AuthorityError("INVALID_DEMO_IDENTITY", "本地会话只接受固定的 persona 选择。");
        }
        return json(response, 201, identities.createAgentSession(input.persona));
      } catch (error) {
        if (error instanceof AuthorityError) return json(response, 400, { error: error.code, message: error.message });
        throw error;
      }
    }
    let identity;
    if (url.pathname.startsWith("/api/")) {
      try {
        identity = identities.authenticate(request.headers.authorization);
        const allowedRoles = requiredRoles(request.method, url.pathname);
        if (!allowedRoles) return json(response, 404, { error: "NOT_FOUND" });
        assertIdentityRole(identity, allowedRoles);
      } catch (error) {
        if (error instanceof AuthorityError) {
          const status = error.code === "UNAUTHENTICATED" ? 401 : 403;
          return json(response, status, { error: error.code, message: error.message });
        }
        throw error;
      }
    }
    const now = Date.now();
    const expiredRequests = Object.values(state.consentRequests).filter((record) =>
      record.ownerId === identity?.subject && record.tenantId === identity?.tenantId &&
      record.status === "pending" && record.expiresAt <= now);
    if (expiredRequests.length) {
      commit((next) => {
        for (const record of expiredRequests) {
          next.consentRequests[record.id].status = "expired";
          next.consentRequests[record.id].resolvedAt = now;
          const challenge = next.resourceChallenges[record.resourceChallengeId];
          if (challenge?.status === "open") challenge.status = "expired";
          next.events.push({
            id: `evt-${next.sequence++}`, type: "consent.expired", paymentId: null,
            taskId: record.taskId, consentRequestId: record.id, at: new Date(now).toISOString(),
          });
        }
      });
    }
    if (url.pathname.startsWith("/api/commerce/v1/")) {
      return handleCommerceApi(request, response, url, identity, state, commit, planner);
    }
    if (request.method === "GET" && url.pathname === "/api/state") return json(response, 200, snapshot(state, identity));
    if (request.method === "POST" && url.pathname === "/api/reset") {
      const rejected = mutationError(request);
      if (rejected) return json(response, rejected.status, rejected);
      try {
        await readBody(request);
      } catch (error) {
        if (error instanceof AuthorityError) return json(response, 400, { error: error.code, message: error.message });
        throw error;
      }
      commit((next) => resetTenantState(next, identity.tenantId));
      return json(response, 200, snapshot(state, identity));
    }
    if (url.pathname.startsWith("/api/")) {
      const taskLookup = url.pathname.match(/^\/api\/tasks\/([^/]+)$/);
      if (request.method === "GET" && taskLookup) {
        const task = state.tasks[taskLookup[1]];
        if (!task || task.ownerId !== identity.subject || task.tenantId !== identity.tenantId) {
          return json(response, 404, { error: "TASK_NOT_FOUND" });
        }
        return json(response, 200, task);
      }
      if (request.method !== "POST") return json(response, 405, { error: "METHOD_NOT_ALLOWED" });
      const rejected = mutationError(request);
      if (rejected) return json(response, rejected.status, rejected);
      try {
        const input = await readBody(request);
        assertNoClientIdentity(input);
        const scopedInput = { ...input, ownerId: identity.subject, tenantId: identity.tenantId };
        let result;
        const taskAction = url.pathname.match(/^\/api\/tasks\/([^/]+)\/actions$/);
        if (url.pathname === "/api/tasks" && request.method === "POST") {
          const task = await proposeTask(scopedInput, planner);
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
          return json(response, 201, { result, state: snapshot(state, identity) });
        }
        if (taskAction) {
          result = commit((next) => requestTaskAction(next, {
            ...scopedInput,
            taskId: taskAction[1],
          }));
          return json(response, 200, { result, state: snapshot(state, identity) });
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
              ownerId: identity.subject,
              tenantId: identity.tenantId,
              taskId: input.taskId,
              consentId: input.consentId,
              idempotencyKey: input.idempotencyKey,
              resourceChallengeId: input.challengeId,
            });
            const delivery = deliverPaidResource(next, {
              ownerId: identity.subject,
              tenantId: identity.tenantId,
              paymentId: payment.id,
            });
            return { payment, delivery };
          });
          return json(response, 200, { result, state: snapshot(state, identity) });
        }
        switch (url.pathname) {
          case "/api/consents":
            result = commit((next) => createTaskConsent(next, { ...scopedInput }));
            break;
          case "/api/consents/revoke":
            result = commit((next) => revokeConsent(next, { ...scopedInput }));
            break;
          case "/api/payments":
            result = commit((next) => createPayment(next, { ...scopedInput }));
            break;
          case "/api/payments/reconcile":
            result = commit((next) => {
              const payment = next.payments[input.paymentId];
              if (!payment || payment.ownerId !== identity.subject || payment.tenantId !== identity.tenantId) {
                throw new AuthorityError("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
              }
              return reconcilePayment(next, input);
            });
            break;
          case "/api/payments/fulfill":
            result = commit((next) => fulfillPayment(next, { ...scopedInput }));
            break;
          case "/api/payments/fulfillment/fail":
            result = commit((next) => recordFulfillmentFailure(next, { ...scopedInput }));
            break;
          case "/api/payments/fulfillment/resolve":
            result = commit((next) => resolveFulfillment(next, { ...scopedInput }));
            break;
          case "/api/payments/refund":
            result = commit((next) => refundPayment(next, { ...scopedInput }));
            break;
          case "/api/payments/events":
            result = commit((next) => {
              const payment = next.payments[input.paymentId];
              if (!payment || payment.ownerId !== identity.subject || payment.tenantId !== identity.tenantId) {
                throw new AuthorityError("PAYMENT_NOT_FOUND", "付款不存在或不属于此用户/租户。");
              }
              return applyPaymentEvent(next, input);
            });
            break;
          default:
            return json(response, 404, { error: "NOT_FOUND" });
        }
        return json(response, 200, { result, state: snapshot(state, identity) });
      } catch (error) {
        if (error instanceof AuthorityError) {
          const status = error.code.endsWith("_NOT_FOUND") ? 404 : 400;
          return json(response, status, { error: error.code, message: error.message });
        }
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
  const identities = createIdentityRegistry();
  const handler = createHandler(statePath, planner, identities);
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
