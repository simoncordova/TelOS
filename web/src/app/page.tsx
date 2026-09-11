import { obtenerSalud } from "@/lib/api";

// Fase 0 de la migración (ver plan): esta página es a propósito solo un
// placeholder que prueba el pipeline completo (build → Docker → EC2 →
// CloudFront → fetch a la API real) antes de portar ningún componente
// real de ui/app.py -- ese trabajo es la Fase 2.
export default async function Home() {
  const salud = await obtenerSalud();

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-4xl font-semibold text-primary">Telos</h1>
      <p className="max-w-md text-foreground/80">
        El nuevo frontend está en construcción. La app completa sigue disponible en
        Streamlit mientras tanto.
      </p>
      <p className="rounded-full bg-surface px-4 py-1 text-sm">
        API:{" "}
        {salud ? (
          <span className="text-primary">conectada ({salud.estado})</span>
        ) : (
          <span className="text-foreground/60">sin conexión</span>
        )}
      </p>
    </main>
  );
}
