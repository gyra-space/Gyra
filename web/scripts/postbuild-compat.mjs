// Post-build pass: lower modern JS syntax (||=, &&=, ??=) in the static export
// output so older browsers (Edge/Chrome 80+) can parse all chunks.
//
// Why: Next's SWC minifier re-introduces logical assignment operators
// regardless of browserslist, and some dependencies ship them in source.
// See https://github.com/vercel/next.js - SWC minify does not honor env targets.
//
// Runs automatically via the "postbuild" npm hook after `next build`.
import { readdirSync, statSync, readFileSync, writeFileSync } from 'fs';
import path from 'path';
import { transform } from 'esbuild';

const OUT_DIR = path.resolve(process.cwd(), 'out');
const TARGET = 'es2020'; // Edge/Chrome 80+: keeps ?. and ??, lowers ||= &&= ??=

function collectJsFiles(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = statSync(full);
    if (stat.isDirectory()) collectJsFiles(full, acc);
    else if (name.endsWith('.js')) acc.push(full);
  }
  return acc;
}

async function main() {
  const files = collectJsFiles(OUT_DIR);
  let changed = 0;
  for (const file of files) {
    const src = readFileSync(file, 'utf8');
    // Skip files that already avoid ES2021 syntax.
    if (!/\|\|=|&&=|\?\?=/.test(src)) continue;
    const { code } = await transform(src, {
      target: TARGET,
      legalComments: 'inline',
    });
    writeFileSync(file, code);
    changed++;
  }
  console.log(
    `[postbuild-compat] lowered syntax to ${TARGET} in ${changed}/${files.length} JS files under out/`
  );
}

main().catch(err => {
  console.error('[postbuild-compat] failed:', err);
  process.exit(1);
});
