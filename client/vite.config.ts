import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      jsxImportSource: "@emotion/react",
      babel: {
        plugins: ["@emotion/babel-plugin"],
      },
    }),
    tailwindcss()
  ],
  server: {
    host: true,
    port: 3000,
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
  preview: {
    host: true,
    port: 3000,
  },
});
