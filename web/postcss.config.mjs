// autoprefixer 依据 package.json browserslist 目标补 -webkit-/-ms- 前缀，
// 覆盖 backdrop-filter、user-select、appearance 等老内核（旧 Chromium/Safari）前缀缺口
const config = {
  plugins: ["@tailwindcss/postcss", "autoprefixer"],
};

export default config;
