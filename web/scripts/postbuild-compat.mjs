// Post-build pass: lower modern JS/CSS syntax in the static export output so
// older browsers (Edge/Chrome 80+) can render the app.
//
// Why:
// - Next's SWC minifier re-introduces logical assignment operators regardless
//   of browserslist, and some dependencies ship them in source.
// - Tailwind CSS v4 wraps its output in @layer at-rules which Chromium < 99
//   (Edge < 99) does not recognize, causing the entire stylesheet to be dropped.
// - Tailwind v4 also uses oklch(), color-mix(), clamp(), :is(), :where(),
//   line-clamp, fit-content etc. which are unsupported or only partially
//   supported in Edge/Chrome 80.
//
// Runs automatically via the "postbuild" npm hook after `next build`.
import { readdirSync, statSync, readFileSync, writeFileSync } from 'fs';
import path from 'path';
import { transform as esbuildTransform } from 'esbuild';

const OUT_DIR = path.resolve(process.cwd(), 'out');
const JS_TARGET = 'es2020'; // Edge/Chrome 80+: keeps ?. and ??, lowers ||= &&= ??=
// CSS targets for Lightning CSS. We resolve to explicit versions because
// lightningcss's browserslistToTargets does not accept range queries.
const CSS_QUERIES = ['chrome >= 80', 'edge >= 80'];

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

async function lowerCss() {
  const cssDir = path.join(OUT_DIR, '_next', 'static', 'css');
  let changed = 0;
  let total = 0;
  try {
    const { transform: lightningTransform, browserslistToTargets } = await import('lightningcss');
    const { default: postcss } = await import('postcss');
    const { default: browserslist } = await import('browserslist');

    // Lightning CSS wants explicit versions (e.g. 'chrome 80'), not ranges.
    const resolved = browserslist(CSS_QUERIES);
    const targets = browserslistToTargets(resolved);

    const stripLayerPlugin = () => ({
      postcssPlugin: 'strip-layers',
      AtRule: {
        layer(atRule) {
          if (atRule.nodes && atRule.nodes.length) {
            atRule.replaceWith(atRule.nodes);
          } else {
            atRule.remove();
          }
        },
      },
    });
    stripLayerPlugin.postcss = true;

    // Split a selector list by top-level commas (ignoring commas inside
    // parentheses, e.g. :is(...), :-webkit-any(...)).
    function splitTopLevelCommas(str) {
      const parts = [];
      let depth = 0;
      let current = '';
      for (const ch of str) {
        if (ch === '(') depth++;
        else if (ch === ')') depth--;
        if (ch === ',' && depth === 0) {
          parts.push(current.trim());
          current = '';
          continue;
        }
        current += ch;
      }
      const last = current.trim();
      if (last) parts.push(last);
      return parts;
    }

    function expandWhere(sel) {
      sel = sel.trim();
      // Bare :where(X) -> X
      const bare = sel.match(/^:where\((.*)\)$/s);
      if (bare) return splitTopLevelCommas(bare[1]).join(', ');
      // A:where(X) -> A X1, A X2, ...
      const suffix = sel.match(/^(.+):where\((.*)\)$/s);
      if (suffix) {
        const base = suffix[1].trim();
        return splitTopLevelCommas(suffix[2])
          .map((s) => `${base}${s}`)
          .join(', ');
      }
      // :where(X) B -> X1 B, X2 B, ...
      const prefix = sel.match(/^:where\((.*)\)\s+(.+)$/s);
      if (prefix) {
        const rest = prefix[2].trim();
        return splitTopLevelCommas(prefix[1])
          .map((s) => `${s} ${rest}`)
          .join(', ');
      }
      // A :where(X) -> A X1, A X2, ...
      const spaced = sel.match(/^(.+)\s+:where\((.*)\)$/s);
      if (spaced) {
        const base = spaced[1].trim();
        return splitTopLevelCommas(spaced[2])
          .map((s) => `${base} ${s}`)
          .join(', ');
      }
      return sel;
    }

    // Manual fallbacks for things Lightning CSS does not handle.
    const fallbackPlugin = () => ({
      postcssPlugin: 'compat-fallbacks',
      Declaration: {
        // Chrome 80 needs -webkit-fit-content.
        'width'(decl) {
          if (/\bfit-content\b/.test(decl.value) && !/-webkit-fit-content/.test(decl.value)) {
            decl.cloneBefore({ value: decl.value.replace(/\bfit-content\b/g, '-webkit-fit-content') });
          }
        },
        'min-width'(decl) {
          if (/\bfit-content\b/.test(decl.value) && !/-webkit-fit-content/.test(decl.value)) {
            decl.cloneBefore({ value: decl.value.replace(/\bfit-content\b/g, '-webkit-fit-content') });
          }
        },
        'max-width'(decl) {
          if (/\bfit-content\b/.test(decl.value) && !/-webkit-fit-content/.test(decl.value)) {
            decl.cloneBefore({ value: decl.value.replace(/\bfit-content\b/g, '-webkit-fit-content') });
          }
        },
        'height'(decl) {
          if (/\bfit-content\b/.test(decl.value) && !/-webkit-fit-content/.test(decl.value)) {
            decl.cloneBefore({ value: decl.value.replace(/\bfit-content\b/g, '-webkit-fit-content') });
          }
        },
        'min-height'(decl) {
          if (/\bfit-content\b/.test(decl.value) && !/-webkit-fit-content/.test(decl.value)) {
            decl.cloneBefore({ value: decl.value.replace(/\bfit-content\b/g, '-webkit-fit-content') });
          }
        },
        'max-height'(decl) {
          if (/\bfit-content\b/.test(decl.value) && !/-webkit-fit-content/.test(decl.value)) {
            decl.cloneBefore({ value: decl.value.replace(/\bfit-content\b/g, '-webkit-fit-content') });
          }
        },
        // Old WebKit line-clamp.
        'line-clamp'(decl) {
          if (!/-webkit-line-clamp/.test(decl.prop)) {
            decl.cloneBefore({ prop: '-webkit-line-clamp', value: decl.value });
          }
        },
      },
      Rule(rule) {
        // Expand :where(...) selectors. This increases specificity,
        // but is acceptable for compat.
        if (!/:where\(/.test(rule.selector)) return;
        const expanded = rule.selector
          .split(',')
          .map(expandWhere)
          .join(', ');
        if (expanded !== rule.selector) {
          rule.selector = expanded;
        }
      },
    });
    fallbackPlugin.postcss = true;

    const files = collectFiles(cssDir, '.css');
    total = files.length;
    if (total === 0) return { changed, total };

    for (const file of files) {
      const src = readFileSync(file, 'utf8');
      let css = src;

      // Step 1: Lightning CSS downlevels colors, clamp(), :is(), vendor prefixes, etc.
      if (/@layer\b|oklch\(|color-mix\(|clamp\(|fit-content|:is\(|:where\(|line-clamp/.test(src)) {
        try {
          const result = lightningTransform({
            filename: file,
            code: Buffer.from(src),
            targets,
            minify: false,
          });
          css = result.code.toString('utf8');
        } catch (err) {
          console.warn(`[postbuild-compat] Lightning CSS failed for ${file}: ${err.message}`);
        }
      }

      // Step 2: Manual fallbacks + @layer stripping.
      if (/@layer\b|:where\(|fit-content|line-clamp/.test(css)) {
        const postcssResult = await postcss([fallbackPlugin(), stripLayerPlugin()]).process(css, {
          from: file,
          to: file,
        });
        css = postcssResult.css;
      }

      // Final brute-force cleanup for a few :where() patterns that PostCSS
      // expansion misses (nested parentheses / quote handling).
      const whereReplacements = [
        [
          ':where(select:-webkit-any([multiple], [size])) optgroup option',
          'select:-webkit-any([multiple], [size]) optgroup option',
        ],
        [
          ':where(select:is([multiple], [size])) optgroup option',
          'select:is([multiple], [size]) optgroup option',
        ],
        [
          ':where(select:-webkit-any([multiple], [size])) optgroup',
          'select:-webkit-any([multiple], [size]) optgroup',
        ],
        [
          ':where(select:is([multiple], [size])) optgroup',
          'select:is([multiple], [size]) optgroup',
        ],
        [
          ':where([type="button"], [type="reset"], [type="submit"])',
          '[type="button"], [type="reset"], [type="submit"]',
        ],
        [':where(.css-dev-only-do-not-override-18iikkb)', '.css-dev-only-do-not-override-18iikkb'],
      ];
      let cleaned = css;
      for (const [oldStr, newStr] of whereReplacements) {
        cleaned = cleaned.split(oldStr).join(newStr);
      }
      if (cleaned !== css) {
        css = cleaned;
      }

      if (css !== src) {
        writeFileSync(file, css);
        changed++;
      }
    }
  } catch (err) {
    console.warn('[postbuild-compat] CSS lowering skipped:', err.message);
  }
  return { changed, total };
}

async function main() {
  const js = await lowerJs();
  const css = await lowerCss();
  console.log(
    `[postbuild-compat] JS: lowered to ${JS_TARGET} in ${js.changed}/${js.total} files; CSS: lowered/stripped in ${css.changed}/${css.total} files`
  );
}

main().catch(err => {
  console.error('[postbuild-compat] failed:', err);
  process.exit(1);
});
