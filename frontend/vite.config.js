import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Backend CORS ayarı bu porta izin veriyor; port doluysa başka porta kaymasın, hata versin.
    strictPort: true,
  },
})
