// Lado navegador del framing de api/sse.py -- lee la respuesta de
// fetch() como stream y parsea los mismos frames
// "event: <nombre>\ndata: <json>\n\n" que produce el backend, en el
// mismo orden en que llegan (una cascada de cambio de fase entrega más
// de un mensaje por turno).
export async function* leerEventosSSE(
  respuesta: Response,
): AsyncGenerator<{ evento: string; datos: unknown }> {
  if (!respuesta.body) return;
  const lector = respuesta.body.getReader();
  const decodificador = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await lector.read();
    if (done) break;
    buffer += decodificador.decode(value, { stream: true });

    let indiceSeparador: number;
    while ((indiceSeparador = buffer.indexOf("\n\n")) !== -1) {
      const bloque = buffer.slice(0, indiceSeparador);
      buffer = buffer.slice(indiceSeparador + 2);

      let evento = "message";
      let datosCrudos = "";
      for (const linea of bloque.split("\n")) {
        if (linea.startsWith("event: ")) evento = linea.slice(7);
        else if (linea.startsWith("data: ")) datosCrudos = linea.slice(6);
      }
      if (datosCrudos) yield { evento, datos: JSON.parse(datosCrudos) };
    }
  }
}
