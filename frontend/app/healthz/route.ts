export async function GET() {
  try {
    const response = await fetch(
      `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/health`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      },
    );
    return Response.json(
      { status: response.ok ? "ok" : "unavailable" },
      { status: response.ok ? 200 : 503 },
    );
  } catch {
    return Response.json({ status: "unavailable" }, { status: 503 });
  }
}
export const dynamic = "force-dynamic";
