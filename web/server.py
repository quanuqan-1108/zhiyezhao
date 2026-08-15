"""职业照小能手 Web 后端（FastAPI）。

路由：
  POST /api/upload               上传用户照片，返回 task_id
  POST /api/generate/baseline    生成基准照
  POST /api/generate/rest        生成其余 5 张
  POST /api/revise/{task_id}/{idx}   单张修改
  GET  /api/photo/{task_id}/{idx}    获取某张照片（jpg）
  GET  /api/task/{task_id}       获取任务状态
  GET  /api/download/{task_id}/{idx} 下载单张
  GET  /api/download/{task_id}/all   打包下载 zip
  GET  /api/prompt/{task_id}/{idx}   查看提示词
  GET  /                          静态首页
"""
import asyncio
import io
import json
import time
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import seedream
import task_manager as tm

WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
UPLOAD_DIR = WEB_DIR / "uploads"
OUTPUT_DIR = WEB_DIR / "outputs"

app = FastAPI(title="职业照小能手 Web")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ========== 首页 ==========
@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


# ========== 上传照片 ==========
@app.post("/api/upload")
async def upload(
    photo: UploadFile = File(...),
    field: str = Form(...),
    use_case: str = Form(...),
    style: str = Form(...),
    wear_glasses: str = Form("true"),
    framing: str = Form("半身"),
):
    """上传用户照片 + 选择参数，创建任务。"""
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(400, "仅支持图片文件")

    task = tm.create_task(
        field=field, use_case=use_case, style=style,
        wear_glasses_default=(wear_glasses.lower() == "true"),
        framing=framing,
    )

    suffix = Path(photo.filename or "user.jpg").suffix or ".jpg"
    user_img = UPLOAD_DIR / f"{task['task_id']}_user{suffix}"
    user_img.parent.mkdir(parents=True, exist_ok=True)
    content = await photo.read()
    if len(content) < 1024:
        raise HTTPException(400, "图片文件过小")
    user_img.write_bytes(content)
    tm.set_user_image(task, str(user_img))
    tm.persist_task(task)

    return JSONResponse({
        "task_id": task["task_id"],
        "user_image_url": f"/api/user_image/{task['task_id']}",
        "field": task["field"],
        "use_case": task["use_case"],
        "style": task["style"],
        "framing": task["framing"],
        "wear_glasses": task["wear_glasses_default"],
    })


@app.get("/api/user_image/{task_id}")
def get_user_image(task_id: str):
    task = tm.load_task_from_disk(task_id)
    if not task or not task.get("user_image"):
        raise HTTPException(404, "用户图不存在")
    return FileResponse(task["user_image"])


# ========== 生成基准照 ==========
@app.post("/api/generate/baseline/{task_id}")
async def generate_baseline(task_id: str):
    task = tm.load_task_from_disk(task_id)
    if not task or not task.get("user_image"):
        raise HTTPException(404, "任务不存在或用户图缺失")

    # 任务结构反序列化后 user_image 等可能已序列化。重新拿原始 task dict
    orig = tm.TASKS.get(task_id)
    if orig is None:
        # 从序列化恢复必要字段
        task_dir = OUTPUT_DIR / f"task_{task_id}"
        user_image = task.get("user_image")
        framing = task.get("framing", "半身")
        style = task.get("style", "知性亲和")
        field = task.get("field", "企业管理")
        style_hint = tm.STYLE_BY_FIELD.get(field, tm.STYLE_BY_FIELD["其他"])
        framing_hint = "half-body shot (waist up)" if framing == "半身" else "three-quarter body shot (about knee up)"
        orig = {
            "task_id": task_id, "task_dir": str(task_dir),
            "user_image": user_image, "framing": framing, "style": style,
            "style_hint": style_hint, "framing_hint": framing_hint,
            "field": field, "use_case": task.get("use_case", "自我介绍页"),
        }
        tm.TASKS[task_id] = orig

    spec = tm.PHOTO_SPECS[0]  # 第 1 张：经典正面照
    prompt = tm.build_photo_prompt(orig, spec)
    out_path = Path(orig["task_dir"]) / "01_baseline_classic_front.jpg"

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: seedream.generate(
            prompt=prompt,
            reference_images=[orig["user_image"]],
            output=out_path,
            size="1024x1536",
        ),
    )
    orig["baseline_photo"] = str(out_path)
    tm.record_photo(orig, spec["idx"], spec["name"], str(out_path), prompt, result.get("usage"))
    tm.persist_task(orig)
    return JSONResponse({
        "idx": spec["idx"],
        "name": spec["name"],
        "url": f"/api/photo/{task_id}/{spec['idx']}",
        "prompt": prompt,
        "usage": result.get("usage", {}),
    })


# ========== 生成其余 5 张 ==========
@app.post("/api/generate/rest/{task_id}")
async def generate_rest(task_id: str):
    task = tm.load_task_from_disk(task_id)
    orig = tm.TASKS.get(task_id)
    if not orig or not orig.get("baseline_photo"):
        raise HTTPException(404, "请先生成基准照")

    user_image = orig["user_image"]
    baseline = orig["baseline_photo"]
    task_dir = Path(orig["task_dir"])

    async def gen_one(spec):
        prompt = tm.build_photo_prompt(orig, spec)
        fname = f"{spec['idx']:02d}_{spec['name']}.jpg".replace("/", "_").replace("\\", "_")
        # 文件名用英文 idx 命名，避免中文文件名在 FileResponse 中问题
        safe_fname = f"{spec['idx']:02d}_photo.jpg"
        out_path = task_dir / safe_fname
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda s=spec, p=prompt, o=out_path: seedream.generate(
                prompt=p,
                reference_images=[user_image, baseline],
                output=o,
                size="1024x1536",
            ),
        )
        tm.record_photo(orig, spec["idx"], spec["name"], str(out_path), prompt, result.get("usage"))

    # 串行生成（避免 API 限流）；如需并行改 asyncio.gather
    for spec in tm.PHOTO_SPECS[1:]:
        await gen_one(spec)

    tm.persist_task(orig)
    return JSONResponse({
        "task_id": task_id,
        "photos": [
            {
                "idx": p["idx"], "name": p["name"],
                "url": f"/api/photo/{task_id}/{p['idx']}",
                "prompt": p["prompt"],
                "usage": p.get("usage", {}),
            }
            for p in orig["photos"]
        ],
    })


# ========== 单张修改 ==========
@app.post("/api/revise/{task_id}/{idx}")
async def revise(task_id: str, idx: int, requirement: str = Form(...)):
    orig = tm.TASKS.get(task_id) or tm.load_task_from_disk(task_id)
    if not orig:
        raise HTTPException(404, "任务不存在")
    if idx < 1 or idx > 6:
        raise HTTPException(400, "idx 必须在 1-6")

    user_image = orig["user_image"]
    baseline = orig.get("baseline_photo") or user_image
    task_dir = Path(orig.get("task_dir") or (OUTPUT_DIR / f"task_{task_id}"))

    # 找到该张的 spec 并加修改要求
    spec = next((s for s in tm.PHOTO_SPECS if s["idx"] == idx), None)
    if not spec:
        raise HTTPException(404, f"编号 {idx} 不存在")
    prompt = tm.build_photo_prompt(orig, spec, extra_requirement=requirement)

    out_path = task_dir / f"{idx:02d}_photo.jpg"
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: seedream.generate(
            prompt=prompt,
            reference_images=[user_image, baseline],
            output=out_path,
            size="1024x1536",
        ),
    )
    # 更新该张照片记录
    orig["photos"] = [p for p in orig.get("photos", []) if p["idx"] != idx]
    tm.record_photo(orig, idx, spec["name"], str(out_path), prompt, result.get("usage"))
    tm.persist_task(orig)

    return JSONResponse({
        "idx": idx,
        "name": spec["name"],
        "url": f"/api/photo/{task_id}/{idx}?t={int(time.time())}",
        "prompt": prompt,
        "usage": result.get("usage", {}),
    })


# ========== 照片访问 ==========
@app.get("/api/photo/{task_id}/{idx}")
def get_photo(task_id: str, idx: int):
    task_dir = OUTPUT_DIR / f"task_{task_id}"
    candidates = [
        task_dir / f"{idx:02d}_photo.jpg",
        task_dir / f"01_baseline_classic_front.jpg",
    ]
    for c in candidates:
        if c.exists() and (c.name.startswith(f"{idx:02d}_") or (idx == 1 and c.name == "01_baseline_classic_front.jpg")):
            return FileResponse(str(c))
    raise HTTPException(404, "照片不存在")


@app.get("/api/prompt/{task_id}/{idx}")
def get_prompt(task_id: str, idx: int):
    orig = tm.TASKS.get(task_id)
    if not orig:
        # fallback: 从磁盘读
        t = tm.load_task_from_disk(task_id)
        if not t:
            raise HTTPException(404, "任务不存在")
        photos = t.get("photos", [])
    else:
        photos = orig.get("photos", [])
    p = next((x for x in photos if x["idx"] == idx), None)
    if not p:
        raise HTTPException(404, "照片不存在")
    return JSONResponse({"idx": idx, "name": p["name"], "prompt": p["prompt"], "usage": p.get("usage", {})})


@app.get("/api/task/{task_id}")
def get_task(task_id: str):
    orig = tm.TASKS.get(task_id)
    if not orig:
        t = tm.load_task_from_disk(task_id)
        if not t:
            raise HTTPException(404, "任务不存在")
        return JSONResponse(t)
    return JSONResponse(tm.serialize_task(orig))


# ========== 下载 ==========
@app.get("/api/download/{task_id}/{idx}")
def download_one(task_id: str, idx: int):
    task_dir = OUTPUT_DIR / f"task_{task_id}"
    f = task_dir / f"{idx:02d}_photo.jpg"
    if not f.exists():
        f = task_dir / "01_baseline_classic_front.jpg" if idx == 1 else None
    if not f or not f.exists():
        raise HTTPException(404, "照片不存在")
    return FileResponse(str(f), filename=f"职业照小能手_{idx:02d}.jpg")


@app.get("/api/download/{task_id}/all")
def download_all(task_id: str):
    task_dir = OUTPUT_DIR / f"task_{task_id}"
    if not task_dir.exists():
        raise HTTPException(404, "任务不存在")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(task_dir.glob("*.jpg")):
            zf.write(f, arcname=f.name)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=职业照小能手_{task_id}.zip"},
    )


# ========== 启动入口 ==========
if __name__ == "__main__":
    import os

    import uvicorn

    # Render 等云平台通过 PORT 环境变量注入端口；本地默认 8765
    port = int(os.environ.get("PORT", 8765))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 60)
    print("  职业照小能手 Web 已启动")
    print(f"  访问: http://localhost:{port}")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port, log_level="info")
