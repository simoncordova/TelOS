// Equivalente mínimo de str.format(**valores) para los textos de
// lib/i18n.ts que llevan placeholders ("{usuario_id}", "{racha}", etc.).
export function formatear(plantilla: string, valores: Record<string, string | number>): string {
  return plantilla.replace(/\{(\w+)\}/g, (_, clave) => String(valores[clave] ?? ""));
}
