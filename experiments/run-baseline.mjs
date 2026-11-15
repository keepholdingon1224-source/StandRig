// Compatibility entry point: retain the original, recorded validation code.
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
if (resolve(process.cwd()) !== resolve(root)) {
  throw new Error('Run from the StandRig repository root: node experiments/run-baseline.mjs');
}
await import('../validation/probe.mjs');
