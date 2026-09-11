import type { ReactNode } from "react";

// Streamlit renderiza estos textos con st.markdown (negrita + saltos de
// línea). Los textos reales (agents/*.py, lib/i18n.ts) solo usan
// **negrita** y "\n" -- no hace falta un parser de markdown completo (ni
// la dependencia que eso implicaría) para cubrirlos.
export function textoEnriquecido(texto: string): ReactNode {
  const lineas = texto.split("\n");
  return lineas.map((linea, i) => (
    <span key={i}>
      {renderizarNegritas(linea)}
      {i < lineas.length - 1 && <br />}
    </span>
  ));
}

function renderizarNegritas(linea: string): ReactNode {
  const partes = linea.split(/(\*\*[^*]+\*\*)/g);
  return partes.map((parte, i) =>
    parte.startsWith("**") && parte.endsWith("**") ? (
      <strong key={i}>{parte.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{parte}</span>
    ),
  );
}
