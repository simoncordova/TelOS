import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" -- imagen Docker liviana (solo el server compilado +
  // node_modules podados), en vez de copiar todo node_modules/ al
  // contenedor final. Ver web/Dockerfile.
  output: "standalone",
};

export default nextConfig;
