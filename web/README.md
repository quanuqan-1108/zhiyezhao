# 职业照小能手 Web 系统

基于 FastAPI + 单页 HTML 的全栈交互式讲师形象照生成系统。

## 目录结构

```
web/
├── server.py          FastAPI 主应用（路由）
├── seedream.py        Seedream 5.0 Pro API 薄封装
├── task_manager.py    任务状态管理 + 提示词构建（基于 Skill 工作流）
├── requirements.txt   Python 依赖列表
├── start.bat          Windows 一键启动脚本
├── static/
│   ├── index.html    单页 HTML
│   ├── styles.css    样式
│   └── app.js        前端逻辑
├── uploads/          用户上传的原图（自动创建）
├── outputs/          生成的形象照（按 task_id 分目录）
└── tasks/            任务元数据持久化（JSON）
```

## 启动方式

### 方式一：双击 `start.bat`（推荐）
直接双击 `start.bat`，会自动设置 PYTHONPATH 并启动服务。

### 方式二：手动启动
```bash
cd C:\Users\YaoCa\.workbuddy\skills\职业照小能手\web
PYTHONPATH=C:\Users\YaoCa\.workbuddy\binaries\python\envs\skill_web_deps ^
C:\Users\YaoCa\.workbuddy\binaries\python\versions\3.13.12\python.exe server.py
```

启动后访问 **http://localhost:8765**

## 前置条件

1. **环境变量 ARK_API_KEY**：必须已设置（用户级永久）
   ```powershell
   [Environment]::SetEnvironmentVariable("ARK_API_KEY", "ark-xxxx-xxxx-NNNNN", "User")
   ```
   设置后**重启 CodeBuddy** 让子进程读到。

2. **Python 依赖**：已安装到 `C:\Users\YaoCa\.workbuddy\binaries\python\envs\skill_web_deps`
   - fastapi 0.141.1
   - uvicorn 0.52.3
   - python-multipart 0.0.32
   - pillow 12.3.0

   如需重装：
   ```bash
   C:\Users\YaoCa\.workbuddy\binaries\python\versions\3.13.12\python.exe -m pip install --target C:\Users\YaoCa\.workbuddy\binaries\python\envs\skill_web_deps fastapi uvicorn python-multipart pillow
   ```

## 使用流程

1. **① 上传照片**：点击或拖拽 1~5 张本人正面照到上传区
2. **② 选择参数**：授课领域 / 使用场景 / 风格偏好 / 取景范围 / 是否戴眼镜
3. **③ 确认基准照**：系统按方案的第 1 张（经典正面照）生成基准照，可调整 5 次
4. **④ 一键生成 5 张**：基于基准照 + 原图衍生其余 5 张
5. **⑤ 查看 / 修改 / 下载**：每张支持
   - 🔍 查看大图
   - 📄 查看生成用的提示词
   - ✏️ 输入修改要求重新生成
   - ⬇ 下载单张
   - 📦 一键打包下载全部 6 张（zip）

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload` | 上传照片 + 创建任务 |
| POST | `/api/generate/baseline/{task_id}` | 生成基准照 |
| POST | `/api/generate/rest/{task_id}` | 生成其余 5 张 |
| POST | `/api/revise/{task_id}/{idx}` | 单张修改 |
| GET | `/api/photo/{task_id}/{idx}` | 获取照片 |
| GET | `/api/prompt/{task_id}/{idx}` | 查看提示词 |
| GET | `/api/task/{task_id}` | 获取任务状态 |
| GET | `/api/download/{task_id}/{idx}` | 下载单张 |
| GET | `/api/download/{task_id}/all` | 打包下载 zip |

## 设计原则

- **严格保留五官与发型**：每张生成时把用户原图 + 基准照作为双参考图
- **3:4 竖版 · 1024×1536**：适合 PPT 讲师介绍页 / 课程海报 / 招生简章
- **纯色背景**：纯白 / 纯灰 / 蓝黑三色
- **春秋季着装**：西装、衬衫、薄针织、风衣等职业装
- **AI 标识**：右下角带 "AI生成" 水印（合规要求）
- **安全**：API Key 仅通过环境变量 `ARK_API_KEY` 读取，不落盘

## 注意事项

- 单张生成约 30-60 秒，6 张约 1-2 分钟
- 每张消耗约 4096 tokens，整套 6 张约 24K tokens
- 火山方舟返回的 CDN URL 24 小时有效，但本系统已自动下载到本地（`outputs/task_xxx/`）
- 服务运行期间所有任务缓存在内存中，重启后丢失；建议生成后尽快下载

## 停止服务

按 `Ctrl+C` 或直接关闭命令行窗口即可。
