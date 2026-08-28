import { defineConfig } from 'vite'
import { resolve } from 'path'
import fg from 'fast-glob'

function getInputEntries() {
  const entries: Record<string, string> = {}

  const files = fg.sync('src/**/*.{ts,js}', { cwd: __dirname })

  for (const file of files) {
    // Strip the extension and slashes for the key
    const name = file.replace(/^src\//, '').replace(/\.[tj]s$/, '')
    entries[name] = resolve(__dirname, file)
  }

  return entries
}

export default defineConfig({
    root: '../frontend/',
    base: './', // relative path for output files
    build: {
        outDir: '../static/js/compiled',
        emptyOutDir: true,
        rollupOptions: {
            input: getInputEntries(),
            output: {
                entryFileNames: '[name].js',
                chunkFileNames: '[name].js',
                assetFileNames: '[name][extname]',
            },
        },
    },
    test: {
      environment: 'jsdom', // adds simulated browser calls, i.e., window, document, etc. to the test environment
      globals: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'text-summary'],
        reportsDirectory: './coverage',
        exclude: ['node_modules/', 'test/'],
      },
    },
})
