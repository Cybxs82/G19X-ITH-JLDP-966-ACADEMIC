const apiUrl = process.env.CFO_API_URL ?? "http://localhost:8000/api/v1";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ alertId: string }> },
): Promise<Response> {
  const { alertId } = await params;
  const alertIdNumber = Number(alertId);
  if (!/^[1-9]\d*$/.test(alertId) || !Number.isSafeInteger(alertIdNumber)) {
    return Response.json(
      { detail: "El ID de alerta debe ser un entero positivo." },
      { status: 400 },
    );
  }

  const headers = new Headers();
  const cookie = request.headers.get("cookie");
  const contentType = request.headers.get("content-type");
  if (cookie) headers.set("cookie", cookie);
  if (contentType) headers.set("content-type", contentType);

  try {
    const response = await fetch(`${apiUrl}/alerts/${alertIdNumber}`, {
      method: "PATCH",
      headers,
      body: await request.text(),
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    console.error("Unable to reach the alerts API", error);
    return Response.json(
      { detail: "No se pudo conectar con el servicio de alertas." },
      { status: 502 },
    );
  }
}
