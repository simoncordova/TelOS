// Port 1:1 de _parsear_sistema en ui/app.py: separa el string de
// "sistema" (líneas "Etiqueta: valor", armado por código en
// agents/orquestador.py::SesionTelos._formatear_sistema, no por el
// modelo) en filas para mostrarlas como checklist. Si el texto no sigue
// ese formato (fichas de antes del selector visual), devuelve una sola
// fila con todo el texto tal cual -- nunca falla, solo se degrada a
// texto plano.
export function parsearSistema(sistemaTexto: string): [string, string][] {
  if (!sistemaTexto) return [];
  const filas: [string, string][] = [];
  for (const lineaCruda of sistemaTexto.split("\n")) {
    const linea = lineaCruda.trim();
    if (!linea || !linea.includes(":")) continue;
    const indice = linea.indexOf(":");
    const etiqueta = linea.slice(0, indice).trim();
    const valor = linea.slice(indice + 1).trim();
    if (valor) filas.push([etiqueta, valor]);
  }
  return filas.length > 0 ? filas : [["", sistemaTexto]];
}
