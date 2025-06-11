// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import node from '@astrojs/node';
import auth from 'auth-astro';

// https://astro.build/config
export default defineConfig({
  integrations: [react(), tailwind(), auth()],
  output: 'server', // For SSR capabilities
  adapter: node({
    mode: 'standalone'
  })
});
