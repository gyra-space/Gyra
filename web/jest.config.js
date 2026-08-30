/** @type {import("jest").Config }**/
module.exports = {
  testEnvironment: "jsdom",
  preset: "ts-jest",
  moduleNameMapper: {
    // CSS 规则必须放在 `^@/` 别名之前:`@/xxx/xxx.css` 形式的导入会先被
    // 通配别名命中并映射为真实 css 文件路径,css 后缀规则就永远轮不到
    // (jsdom 无法解析 css,报 "Unexpected token '.'")
    "\\.(css|scss|sass|less)$": "<rootDir>/src/test-style-stub.ts",
    "^@/(.*)$": "<rootDir>/src/$1",
    // @ant-design/x(CJS)内部 require antd/es(ESM);统一映射到 CJS 的 lib 产物
    "^antd/es/(.*)$": "antd/lib/$1",
    "^antd/es$": "antd/lib",
  },
  testMatch: [
    "<rootDir>/src/**/__tests__/**/*.test.ts",
    "<rootDir>/src/**/__tests__/**/*.test.tsx",
  ],
  // Project tsconfig uses jsx: "preserve"; override to react-jsx so ts-jest can
  // transpile .tsx React tests into executable JS under Node/jsdom.
  transform: {
    "^.+\\.tsx?$": ["ts-jest", { tsconfig: { jsx: "react-jsx" } }],
    // unified/remark 生态是纯 ESM,用第二个 ts-jest 实例转译这些 node_modules .js
    // react-syntax-highlighter(dist/esm)、嵌套依赖(如 @antv/gpt-vis/node_modules/react-markdown)
    // 同为纯 ESM,需一并转译
    "^.+/node_modules/(unified|remark-.*|rehype-.*|lowlight|react-markdown|mdast-.*|micromark.*|unist-.*|estree-.*|vfile.*|bail|trough|devlop|zwitch|html-void-elements|stringify-entities|character-entities.*|ccount|comma-separated-tokens|space-separated-tokens|hast-.*|hastscript|parse5|property-information|web-namespaces|decode-named-character-reference|longest-streak|markdown-table|trim-lines|escape-string-regexp|is-plain-obj|extend|html-url-attributes|url-join|react-syntax-highlighter|highlight\\.js|copy-text-to-clipboard|fast-png|iobuffer|jspdf)/.+\\.js$":
      ["ts-jest", { tsconfig: { allowJs: true, jsx: "react-jsx" } }],
  },
  // unified/remark 生态是纯 ESM,允许 ts-jest 转译这些依赖;
  // `.*` 前缀使嵌套 node_modules(如 @antv/gpt-vis/node_modules/react-markdown)同样命中
  transformIgnorePatterns: [
    "node_modules/(?!.*(unified|remark-.*|rehype-.*|lowlight|react-markdown|mdast-.*|micromark.*|unist-.*|estree-.*|vfile.*|bail|trough|devlop|zwitch|html-void-elements|stringify-entities|character-entities.*|ccount|comma-separated-tokens|space-separated-tokens|hast-.*|hastscript|parse5|property-information|web-namespaces|decode-named-character-reference|longest-streak|markdown-table|trim-lines|escape-string-regexp|is-plain-obj|extend|html-url-attributes|url-join|react-syntax-highlighter|highlight\\.js|copy-text-to-clipboard|fast-png|iobuffer|jspdf)/)",
  ],
  // Registers @testing-library/jest-dom matchers (toBeInTheDocument, …) for
  // React component tests that run under the jsdom environment.
  setupFilesAfterEnv: ["<rootDir>/src/test-setup.ts"],
};