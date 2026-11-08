/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "hsl(90 12% 97%)",
        surface: {
          DEFAULT: "#ffffff",
          raised: "#f1f5ee",
          subtle: "#f8faf6",
          border: "hsl(110 9% 85%)",
          hover: "#f3f6f1",
        },
        forest: {
          DEFAULT: "hsl(166 52% 27%)",
          hover: "hsl(166 52% 20%)",
          soft: "hsl(157 28% 92%)",
          text: "#175441",
        },
        ink: {
          DEFAULT: "hsl(160 13% 15%)",
          muted: "hsl(150 6% 40%)",
          subtle: "#64748b",
        }
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
}
