from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    user_id: str
    user_role: str


def get_request_context(
    x_tenant_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> RequestContext:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    if not x_user_role:
        raise HTTPException(status_code=400, detail="Missing X-User-Role header")
    return RequestContext(tenant_id=x_tenant_id, user_id=x_user_id, user_role=x_user_role)


def require_roles(ctx: RequestContext, allowed: set[str]) -> None:
    if ctx.user_role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient role for this action")
