# 职业照小能手 · 职业照生成系统

面向职业讲师的 AI 形象照生成 Web 系统：上传本人照片 → 选择授课领域与使用场景 → 生成 6 张专业职业照（3:4 竖版、春秋职业装、纯色背景），支持查看大图、查看提示词、单张修改、打包下载。

基于 Material Design 3 设计系统构建 UI/UX，支持浅色/深色主题。

## 技术栈

- 后端：Python 3.13 + FastAPI + uvicorn
- 前端：原生 HTML / CSS / JS（Material Design 3 风格，零构建）
- AI：火山方舟 Doubao-Seedream-5.0-pro 图像生成 API

## 本地运行

```bash
cd web
pip install -r requirements.txt
export ARK_API_KEY="你的火山方舟 API Key"   # Windows PowerShell: $env:ARK_API_KEY="..."
python server.py                            # 默认 http://localhost:8765
```

## 部署到 Render

方式一：Blueprint（本仓库已含 `render.yaml`）

1. Fork / 推送本仓库到你的 GitHub
2. Render Dashboard → New → Blueprint → 选择仓库
3. 按提示填入 `ARK_API_KEY`（敏感值，不落仓库）

方式二：手动配置

| 配置项 | 值 |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r web/requirements.txt` |
| Start Command | `cd web && uvicorn server:app --host 0.0.0.0 --port $PORT` |
| 环境变量 | `ARK_API_KEY`（必填）、`PYTHON_VERSION=3.13.12` |

## 目录结构

```
├── render.yaml          Render 部署蓝图
└── web/
    ├── server.py        FastAPI 后端（上传/生成/修改/下载 路由）
    ├── seedream.py      Seedream 5.0 Pro API 封装
    ├── task_manager.py  任务状态 + 提示词构建
    ├── requirements.txt 依赖清单
    └── static/          M3 风格前端（index.html / styles.css / app.js）
```

## 说明

- 运行时目录（uploads/outputs/tasks）按需自动创建；免费实例重启后临时文件会清空
- 生成图片带 AI 水印，符合《人工智能生成合成内容标识办法》
- 系统严格保留用户原五官与发型，仅调整着装、背景、布光
