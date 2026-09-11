import { existsSync, unlinkSync } from "node:fs";
import path from "node:path";

// Limpia los backends locales (data/*.json) antes de correr los e2e --
// TELOS_FICHA_BACKEND=local guarda todo en estos 5 archivos (ver
// tools/*_local.py); sin esto, una corrida anterior deja el usuario de
// prueba con nombre ya guardado y el test de "Paso 0: pide el nombre"
// empieza a fallar en la segunda corrida, no en la primera -- un test
// no determinístico es peor que no tenerlo.
const ARCHIVOS = ["fichas.json", "perfiles.json", "conversaciones.json", "push_suscripciones.json", "uso_diario.json"];

export default function globalSetup() {
  const dirDatos = path.resolve(__dirname, "..", "..", "data");
  for (const archivo of ARCHIVOS) {
    const ruta = path.join(dirDatos, archivo);
    if (existsSync(ruta)) unlinkSync(ruta);
  }
}
