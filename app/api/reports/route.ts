const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

function getForwardedHeaders(request: Request, includeContentType = false): Headers {
  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);
  if (includeContentType) {
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
  }
  return headers;
}

function getForwardedResponseHeaders(response: Response): Headers {
  const headers = new Headers();
  for (const header of ["content-type", "content-disposition"]) {
    const value = response.headers.get(header);
    if (value) headers.set(header, value);
  }
  return headers;
}

export async function GET(request: Request): Promise<Response> {
  const query = new URL(request.url).search;
  try {
    const response = await fetch(`${apiUrl}/reports${query}`, {
      headers: getForwardedHeaders(request),
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: getForwardedResponseHeaders(response),
    });
  } catch (error) {
    console.error("Unable to reach the reports API", error);
    return Response.json(
      { detail: "No se pudo conectar con el servicio de reportes." },
      { status: 502 },
    );
  }
}

export async function POST(request: Request): Promise<Response> {
  try {
    const response = await fetch(`${apiUrl}/reports`, {
      method: "POST",
      headers: getForwardedHeaders(request, true),
      body: await request.text(),
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: getForwardedResponseHeaders(response),
    });
  } catch (error) {
    console.error("Unable to reach the reports API", error);
    return Response.json(
      { detail: "No se pudo conectar con el servicio de reportes." },
      { status: 502 },
    );
  }
}
