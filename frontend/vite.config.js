import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // Or whatever port you prefer for frontend
    proxy: {
      "/api": {
        // Any request starting with /api will be proxied
        target: "http://localhost:8000", // Your FastAPI backend's address
        changeOrigin: true, // Needed for virtual hosting
        rewrite: (path) => path.replace(/^\/api/, ""), // Removes /api from the request before sending to backend
      },
    },
  },
});
