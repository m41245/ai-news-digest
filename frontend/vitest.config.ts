import { defineConfig as defineTestConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineTestConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    css: false,
  },
});
