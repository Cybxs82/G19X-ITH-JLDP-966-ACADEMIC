const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> },
): Promise<Response> {
  const { reportId } = await params;
  if (!/^\d+$/.test(reportId)) {
    return Response.json({ detail: "El identificador del reporte no es válido." }, { status: 400 });
  }

  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("cookie", cookie);

  try {
    const response = await fetch(`${apiUrl}/reports/${reportId}/pdf`, {
      headers,
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    for (const header of ["content-type", "content-disposition"]) {
      const value = response.headers.get(header);
      if (value) responseHeaders.set(header, value);
    }
    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Unable to download the summary report PDF", error);
    return Response.json(
      { detail: "No se pudo conectar con el servicio de reportes." },
      { status: 502 },
    );
  }
}
