const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

export async function GET(request: Request): Promise<Response> {
  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);

  try {
    const response = await fetch(`${apiUrl}/recommendations`, {
      headers,
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    console.error("Unable to reach the recommendations API", error);
    return Response.json(
      { detail: "No se pudo conectar con el servicio de recomendaciones." },
      { status: 502 },
    );
  }
}
