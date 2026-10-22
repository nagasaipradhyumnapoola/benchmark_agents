import { cpSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const standalone = resolve(root, '.next/standalone');
if (!existsSync(resolve(standalone, 'server.js'))) {
  throw new Error('Build the dashboard first with npm run build.');
}
cpSync(resolve(root, '.next/static'), resolve(standalone, '.next/static'), { recursive: true });
if (existsSync(resolve(root, 'public'))) {
  cpSync(resolve(root, 'public'), resolve(standalone, 'public'), { recursive: true });
}
process.env.HOSTNAME = process.env.BENCHLAB_WEB_HOST || '127.0.0.1';
process.env.NEXT_TELEMETRY_DISABLED = '1';
await import(pathToFileURL(resolve(standalone, 'server.js')).href);
