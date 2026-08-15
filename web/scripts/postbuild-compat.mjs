// Post-build pass: lower modern JS/CSS syntax in the static export output so
// older browsers (Edge/Chrome 80+) can render the app.
//
// Why:
// - Next's SWC minifier re-introduces logical assignment operators regardless
//   of browserslist, and some dependencies ship them in source.
// - Tailwind CSS v4 wraps its output in @layer at-rules which Chromium < 99
//   (Edge < 99) does not recognize, causing the entire stylesheet to be dropped.
//
// Runs automatically via the "postbuild" npm hook after `next build`.
import { readdirSync, statSync, readFileSync, writeFileSync } from 'fs';
import path from 'path';
import { transform as esbuildTransform } from 'esbuild';

const OUT_DIR = path.resolve(process.cwd(), 'out');
const JS_TARGET = 'es2020'; // Edge/Chrome 80+: keeps ?. and ??, lowers ||= &&= ??=

function collectFiles(dir, ext, acc = []) {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = statSync(full);
    if (stat.isDirectory()) collectFiles(full, ext, acc);
    else if (name.endsWith(ext)) acc.push(full);
  }
  return acc;
}

async function lowerJs() {
  const files = collectFiles(OUT_DIR, '.js');
  let changed = 0;
  for (const file of files) {
    const src = readFileSync(file, 'utf8');
    // Skip files that already avoid ES2021 syntax.
    if (!/\|\|=|&&=|\?\?=/.test(src)) continue;
    const { code } = await esbuildTransform(src, {
      target: JS_TARGET,
      legalComments: 'inline',
    });
    writeFileSync(file, code);
    changed++;
  }
  return { changed, total: files.length };
}

async function stripCssLayers() {
  const cssDir = path.join(OUT_DIR, '_next', 'static', 'css');
  let changed = 0;
  let total = 0;
  try {
    const files = collectFiles(cssDir, '.css');
    total = files.length;
    if (total === 0) return { changed, total };

    const { default: postcss } = await import('postcss');
    const stripLayerPlugin = () => ({
      postcssPlugin: 'strip-layers',
      AtRule: {
        layer(atRule) {
          if (atRule.nodes && atRule.nodes.length) {
            // Block form: @layer name { ... } -> unwrap contents
            atRule.replaceWith(atRule.nodes);
          } else {
            // Statement form: @layer name, name; -> remove
            atRule.remove();
          }
        },
      },
    });
    stripLayerPlugin.postcss = true;

    for (const file of files) {
      const src = readFileSync(file, 'utf8');
      if (!/@layer\b/.test(src)) continue;
      const { css } = await postcss([stripLayerPlugin()]).process(src, {
        from: file,
        to: file,
      });
      writeFileSync(file, css);
      changed++;
    }
  } catch (err) {
    // PostCSS may not be available; surface but don't break the build.
    console.warn('[postbuild-compat] CSS layer stripping skipped:', err.message);
  }
  return { changed, total };
}

async function main() {
  const js = await lowerJs();
  const css = await stripCssLayers();
  console.log(
    `[postbuild-compat] JS: lowered to ${JS_TARGET} in ${js.changed}/${js.total} files; CSS: stripped @layer in ${css.changed}/${css.total} files`
  );
}

main().catch(err => {
  console.error('[postbuild-compat] failed:', err);
  process.exit(1);
});
