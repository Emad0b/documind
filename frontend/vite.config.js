import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
  plugins: [tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        configure(proxy) {
          proxy.on("proxyReq", (outgoing, request) => {
            if (request.headers.host)
              outgoing.setHeader("Host", request.headers.host);
          });
        },
      },
    },
  },
});
