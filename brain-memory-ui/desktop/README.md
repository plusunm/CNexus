# Tauri Desktop（规划中）

Desktop 端复用 `frontend/` Next.js 构建产物，通过 Tauri 2.0 打包为原生应用。

## 初始化步骤

```bash
cd brain-memory-ui/frontend
npm run build

cd ../desktop
npm create tauri-app@latest . -- --template vanilla-ts
# 配置 tauri.conf.json 指向 ../frontend/out 或 dev server
```

## 本地 API

Desktop 启动时内嵌 Python Runtime API，或通过 sidecar 运行 `api/main.py`。

详见 [Tauri 2.0 文档](https://v2.tauri.app/).
