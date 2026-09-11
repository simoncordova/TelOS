import type { Textos } from "@/lib/i18n";
import { urlExportarFicha } from "@/lib/apiCliente";
import type { Idioma } from "@/lib/types";

// Port de st.download_button en ui/app.py -- acá un link normal a
// GET /api/ficha/exportar alcanza (el backend ya pone
// Content-Disposition: attachment, ver api/main.py::exportar_ficha).
// Deshabilitado si todavía no hay propósito guardado, igual que en
// Streamlit (`disabled=not proposito`).
export function ExportarButton({ idioma, t, tieneProposito }: { idioma: Idioma; t: Textos; tieneProposito: boolean }) {
  return (
    <a
      href={tieneProposito ? urlExportarFicha(idioma) : undefined}
      aria-disabled={!tieneProposito}
      className={`block rounded-full px-4 py-2 text-center text-sm font-medium ${
        tieneProposito ? "bg-primary text-primary-foreground" : "pointer-events-none bg-surface text-foreground/40"
      }`}
    >
      {t.exportar_boton}
    </a>
  );
}
