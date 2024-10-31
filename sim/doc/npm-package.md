# 將專案打包為 NPM Package 步驟說明

## 1. 專案結構設置
確保你的專案結構如下：
```
xxx/
├── src/ # 源代碼目錄
│ ├── .ts # TypeScript 文件
│ └── .wgsl # WGSL shader 文件
├── dist/ # 編譯後的發布文件
├── package.json
└── tsconfig.json
## 2. 配置 package.json
json
{
"name": "xxx",
"version": "1.0.0",
"main": "dist/yyy.js",
"types": "dist/yyy.d.ts",
"files": [
"dist"
],
"scripts": {
"build": "tsc && webpack",
"prepare": "npm run build"
}
}
```
## 3. 配置 TypeScript (tsconfig.json)
```json
{
"compilerOptions": {
"target": "es2018",
"module": "esnext",
"declaration": true,
"outDir": "./dist",
"strict": true,
"moduleResolution": "node",
"esModuleInterop": true,
"skipLibCheck": true
},
"include": ["src//"],
"exclude": ["node_modules"]
}
```
## 4. 配置 Webpack (webpack.config.js)

```js
const path = require('path');
module.exports = {
entry: './src/yyy.ts',
output: {
path: path.resolve(dirname, 'dist'),
filename: 'yyy.js',
library: {
type: 'module'
}
},
experiments: {
outputModule: true
},
module: {
rules: [
{
test: /\.ts$/,
use: 'ts-loader',
exclude: /node_modules/
},
{
test: /\.wgsl$/,
type: 'asset/source'
}
]
},
resolve: {
extensions: ['.ts', '.js']
}
}

```

npm install --save-dev typescript ts-loader webpack webpack-cli

npm run build

npm login

npm publish

npm install xxx

import { zzz } from 'yyy';