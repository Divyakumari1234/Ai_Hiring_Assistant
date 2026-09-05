import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

function equal(actual: string, expected: string) {
  const a = Buffer.from(actual);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function proxy(request: NextRequest) {
  const password = process.env.REVIEW_PASSWORD;
  if (!password || request.nextUrl.pathname === "/healthz")
    return NextResponse.next();
  const header = request.headers.get("authorization") ?? "";
  if (header.startsWith("Basic ")) {
    const decoded = Buffer.from(header.slice(6), "base64").toString();
    const separator = decoded.indexOf(":");
    if (
      separator >= 0 &&
      equal(
        decoded.slice(0, separator),
        process.env.REVIEW_USERNAME ?? "reviewer",
      ) &&
      equal(decoded.slice(separator + 1), password)
    )
      return NextResponse.next();
  }
  return new NextResponse("Sign in to the hiring workspace", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Reachly", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
