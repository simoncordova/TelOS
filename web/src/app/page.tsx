import { obtenerAuthConfig } from "@/lib/api";
import { obtenerUsuarioActual } from "@/lib/auth";
import type { Idioma } from "@/lib/types";
import { LoginScreen } from "@/components/LoginScreen";
import { TelosApp } from "@/components/TelosApp";

// Port del arranque de ui/app.py -- acá dividido en dos responsabilidades
// que Streamlit mezcla en un solo script top-to-bottom: éste (Server
// Component) decide auth/idioma inicial ANTES de renderizar nada
// interactivo; TelosApp (Client Component) es todo lo que necesita
// estado en el navegador (chat, SSE, festejos).
export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ idioma?: string }>;
}) {
  const { idioma: idiomaParam } = await searchParams;
  // Default en inglés: solo cae a español si el ?idioma= lo pide explícito.
  const idioma: Idioma = idiomaParam === "es" ? "es" : "en";

  const [usuario, config] = await Promise.all([obtenerUsuarioActual(), obtenerAuthConfig()]);

  if (!usuario) {
    return <LoginScreen idioma={idioma} />;
  }

  return <TelosApp usuarioId={usuario.usuarioId} requiereLogin={config.requiereLogin} idiomaInicial={idioma} />;
}
