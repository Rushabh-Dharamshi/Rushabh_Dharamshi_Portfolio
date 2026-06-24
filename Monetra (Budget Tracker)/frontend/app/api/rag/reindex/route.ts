/* istanbul ignore file */
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 300;

function backendUrl() {
  const proxyTarget = process.env.API_PROXY_TARGET;
  if (!proxyTarget) {
    throw new Error("API_PROXY_TARGET is not configured.");
  }
  return `${proxyTarget.replace(/\/$/, "")}/api/rag/reindex`;
}

export async function POST(request: NextRequest) {
  const response = await fetch(backendUrl(), {
    method: "POST",
    headers: {
      "Content-Type": request.headers.get("content-type") ?? "application/json",
      Cookie: request.headers.get("cookie") ?? "",
      "X-Monetra-Expected-User-Id": request.headers.get("x-monetra-expected-user-id") ?? "",
    },
    body: await request.text(),
    cache: "no-store",
  });

  const contentType = response.headers.get("content-type") ?? "application/json";
  const payload = await response.text();

  return new NextResponse(payload, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}
