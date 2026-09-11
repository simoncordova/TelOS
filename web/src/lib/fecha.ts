// Port de _fecha_corta en ui/app.py.
export function fechaCorta(fechaIso: string): string {
  if (!fechaIso) return "";
  const d = new Date(fechaIso);
  if (Number.isNaN(d.getTime())) return fechaIso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
