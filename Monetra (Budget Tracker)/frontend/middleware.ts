import { NextRequest, NextResponse } from "next/server";

function unauthorizedResponse(): NextResponse {
  return new NextResponse("Authentication required for this deployment.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Monetra Demo"',
    },
  });
}

function isAuthorized(request: NextRequest): boolean {
  const expectedUsername = process.env.DEMO_ACCESS_USERNAME ?? "";
  const expectedPassword = process.env.DEMO_ACCESS_PASSWORD ?? "";
  if (!expectedUsername || !expectedPassword) {
    return false;
  }

  const authHeader = request.headers.get("authorization");
  if (!authHeader?.startsWith("Basic ")) {
    return false;
  }

  let decoded = "";
  try {
    decoded = atob(authHeader.slice(6));
  } catch {
    return false;
  }
  const separatorIndex = decoded.indexOf(":");
  if (separatorIndex < 0) {
    return false;
  }

  const username = decoded.slice(0, separatorIndex);
  const password = decoded.slice(separatorIndex + 1);
  return username === expectedUsername && password === expectedPassword;
}

export function middleware(request: NextRequest): NextResponse {
  if (process.env.DEMO_ACCESS_ENABLED !== "true") {
    return NextResponse.next();
  }

  if (isAuthorized(request)) {
    return NextResponse.next();
  }

  return unauthorizedResponse();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
