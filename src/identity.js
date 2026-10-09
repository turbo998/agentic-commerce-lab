import { randomUUID } from "node:crypto";
import { AuthorityError } from "./authority.js";

const DEMO_IDENTITIES = Object.freeze({
  alex: { tenantId: "tenant-demo", subject: "alex" },
  sam: { tenantId: "tenant-alt", subject: "sam" },
});

const SESSION_TTL_MS = 60 * 60_000;

export function createIdentityRegistry(now = () => Date.now()) {
  const sessions = new Map();

  function issue(persona, role) {
    const identity = DEMO_IDENTITIES[persona];
    if (!identity) {
      throw new AuthorityError("INVALID_DEMO_IDENTITY", "请选择固定的本地合成演示身份。");
    }
    const token = randomUUID();
    sessions.set(token, { ...identity, role, expiresAt: now() + SESSION_TTL_MS });
    return { mode: "synthetic-local-identity", ...identity, expiresInSeconds: SESSION_TTL_MS / 1000, token };
  }

  return {
    createAgentSession(persona) {
      const session = issue(persona, "agent");
      return {
        mode: session.mode,
        tenantId: session.tenantId,
        subject: session.subject,
        expiresInSeconds: session.expiresInSeconds,
        agentToken: session.token,
      };
    },
    createHumanSession(persona) {
      const session = issue(persona, "human");
      return {
        mode: session.mode,
        tenantId: session.tenantId,
        subject: session.subject,
        expiresInSeconds: session.expiresInSeconds,
        humanToken: session.token,
      };
    },
    authenticate(header) {
      const match = /^Bearer ([0-9a-f-]{36})$/i.exec(header ?? "");
      const session = match && sessions.get(match[1]);
      if (!session || session.expiresAt <= now()) {
        if (match) sessions.delete(match[1]);
        throw new AuthorityError("UNAUTHENTICATED", "需要有效的本地合成演示会话。");
      }
      return { ...session };
    },
  };
}

export function assertIdentityRole(identity, roles) {
  if (!roles.includes(identity.role)) {
    throw new AuthorityError("FORBIDDEN_ROLE", "此操作不属于当前本地会话角色。");
  }
}

export function assertNoClientIdentity(input) {
  if (Object.hasOwn(input, "ownerId") || Object.hasOwn(input, "tenantId") || Object.hasOwn(input, "subject")) {
    throw new AuthorityError("CLIENT_IDENTITY_FORBIDDEN", "主体与租户由服务端认证上下文确定，不接受请求正文指定。");
  }
}
