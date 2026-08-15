"""任务管理与提示词构建（基于 Skill 工作流）。

负责：
- 任务创建 / 状态查询
- 6 张照片的提示词构建（按 references/portrait_design_spec.md）
- 单张修改的提示词调整
"""
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

SKILL_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = WEB_DIR / "uploads"
OUTPUT_DIR = WEB_DIR / "outputs"
TASKS_DIR = WEB_DIR / "tasks"

# 任务内存状态（简化；生产应使用 DB 或文件持久化）
TASKS: Dict[str, dict] = {}

# 6 张照片的默认设计规格
PHOTO_SPECS = [
    {
        "idx": 1, "name": "经典正面照",
        "pose": "natural front-facing standing, relaxed shoulders",
        "expression": "confident smile, slight upturned lips, smiling eyes",
        "outfit": "navy blue tailored suit with crisp white shirt inside",
        "background": "pure white solid background",
        "lighting": "butterfly lighting, top-soft, soft cheeks",
        "wear_glasses": True,
    },
    {
        "idx": 2, "name": "授课风采照",
        "pose": "front-facing, holding a presentation clicker in one hand or making an explanatory hand gesture",
        "expression": "friendly smile, slight upturned lips, smiling eyes",
        "outfit": "dark charcoal suit with a silk scarf tied elegantly at neck, white shirt inside",
        "background": "pure gray solid background",
        "lighting": "ring soft light, balanced illumination",
        "wear_glasses": True,
    },
    {
        "idx": 3, "name": "亲和侧脸照",
        "pose": "3/4 left side profile, body slightly turned",
        "expression": "gentle soft smile, relaxed lips, smiling eyes",
        "outfit": "light beige thin knit top",
        "background": "dark blue-black solid background",
        "lighting": "ring soft light, soft cheeks",
        "wear_glasses": False,
    },
    {
        "idx": 4, "name": "讲台情境照",
        "pose": "3/4 right side profile, body slightly turned, holding a book or lecture notes in one hand",
        "expression": "gentle smile",
        "outfit": "camel thin knit sweater with collared shirt underneath",
        "background": "pure gray solid background",
        "lighting": "ring soft light, balanced",
        "wear_glasses": False,
    },
    {
        "idx": 5, "name": "气质正侧照",
        "pose": "full side profile, body turned 90 degrees, slight over-the-shoulder glance",
        "expression": "gentle, calm with subtle smile",
        "outfit": "spring/autumn trench coat over thin knit blouse",
        "background": "pure gray solid background",
        "lighting": "Rembrandt lighting, dramatic side light, strong 3D feel",
        "wear_glasses": False,
    },
    {
        "idx": 6, "name": "权威氛围照",
        "pose": "arms crossed confidently or naturally relaxed at sides",
        "expression": "warm gaze with subtle smile, confident and authoritative",
        "outfit": "dark navy business suit with white shirt",
        "background": "dark blue-black solid background",
        "lighting": "Rembrandt lighting, dramatic side light, strong 3D feel",
        "wear_glasses": True,
    },
]

STYLE_BY_FIELD = {
    "企业管理": "professional, authoritative, dark suit",
    "金融": "authoritative, stable, dark formal suit",
    "法律": "authoritative, stable, dark formal suit",
    "IT": "smart, business casual, modern",
    "互联网": "smart, business casual, modern",
    "人文艺术": "elegant, intellectual, with design sense",
    "亲子教育": "warm, friendly, gentle",
    "健康": "kind, dignified, soft and elegant",
    "心理": "kind, dignified, soft and elegant",
    "礼仪": "elegant, dignified",
    "其他": "professional, friendly",
}

USE_CASE_LABEL = {
    "自我介绍页": "自我介绍页主形象",
    "课程海报": "课程海报主体",
    "招生简章": "招生简章",
    "讲师介绍PPT": "讲师介绍 PPT",
    "课程开场页": "课程开场页",
    "其他": "培训相关",
}


def create_task(field: str, use_case: str, style: str,
                wear_glasses_default: bool, framing: str) -> dict:
    """创建新任务，返回任务对象。"""
    task_id = uuid.uuid4().hex[:12]
    task_dir = OUTPUT_DIR / f"task_{task_id}"
    task_dir.mkdir(parents=True, exist_ok=True)

    style_hint = STYLE_BY_FIELD.get(field, STYLE_BY_FIELD["其他"])
    framing_hint = "half-body shot (waist up)" if framing == "半身" else "three-quarter body shot (about knee up)"

    task = {
        "task_id": task_id,
        "field": field,
        "use_case": use_case,
        "style": style,
        "wear_glasses_default": wear_glasses_default,
        "framing": framing,
        "style_hint": style_hint,
        "framing_hint": framing_hint,
        "task_dir": str(task_dir),
        "user_image": None,           # 用户原图路径
        "baseline_photo": None,        # 基准照路径
        "photos": [],                  # 已生成照片列表
        "created_at": time.time(),
        "status": "pending",
    }
    TASKS[task_id] = task
    return task


def get_task(task_id: str) -> Optional[dict]:
    return TASKS.get(task_id)


def set_user_image(task: dict, image_path: str) -> None:
    task["user_image"] = image_path


def build_photo_prompt(task: dict, spec: dict, extra_requirement: str = "") -> str:
    """按 Skill 规范构建单张照片的提示词。"""
    framing = task["framing_hint"]
    glasses_line = "keep the thin-rimmed round glasses" if spec["wear_glasses"] else "no glasses"
    extra = f" Additional requirement: {extra_requirement}." if extra_requirement else ""

    prompt = (
        f"Single-person professional photo for an enterprise trainer. {framing}, 3:4 portrait orientation. "
        "STRICTLY KEEP all facial features and hairstyle of the reference image: oval face, "
        "thin-rimmed round glasses if present, warm-white skin, long black hair with middle parting, "
        "hair naturally draped, slight side-swept bangs near cheeks. "
        f"Pose: {spec['pose']}. "
        f"Expression: {spec['expression']}. "
        f"Outfit: {spec['outfit']}, spring/autumn professional attire, no casual wear. "
        f"Accessories: {glasses_line}. "
        f"Lighting: {spec['lighting']}. "
        f"Background: {spec['background']}. "
        "Composition: subject centered, reasonable headroom, 3:4 portrait. "
        "Quality: high resolution, realistic skin texture, clear hair strands, 1024x1536px."
        + extra
    )
    return prompt


def record_photo(task: dict, idx: int, name: str, output_path: str, prompt: str,
                 usage: dict = None) -> None:
    """记录一张照片生成完成。"""
    task["photos"].append({
        "idx": idx,
        "name": name,
        "output_path": output_path,
        "prompt": prompt,
        "usage": usage or {},
        "generated_at": time.time(),
    })
    task["status"] = "photos_ready" if len(task["photos"]) == 6 else "partial"


def revise_photo(task: dict, idx: int, extra_requirement: str) -> dict:
    """构建修改后的提示词。"""
    spec = next((s for s in PHOTO_SPECS if s["idx"] == idx), None)
    if not spec:
        raise ValueError(f"无效的照片编号 {idx}")
    prompt = build_photo_prompt(task, spec, extra_requirement)
    return {"idx": idx, "prompt": prompt, "spec": spec}


def serialize_task(task: dict) -> dict:
    """序列化任务（去除内部字段）。"""
    return {
        "task_id": task["task_id"],
        "field": task["field"],
        "use_case": task["use_case"],
        "use_case_label": USE_CASE_LABEL.get(task["use_case"], task["use_case"]),
        "style": task["style"],
        "framing": task["framing"],
        "status": task["status"],
        "user_image": task["user_image"],
        "baseline_photo": task["baseline_photo"],
        "photos": [
            {
                "idx": p["idx"],
                "name": p["name"],
                "url": f"/api/photo/{task['task_id']}/{p['idx']}",
                "prompt": p["prompt"],
                "usage": p["usage"],
                "generated_at": p["generated_at"],
            }
            for p in task["photos"]
        ],
    }


def persist_task(task: dict) -> None:
    """持久化任务到磁盘（可选）。"""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    task_file = TASKS_DIR / f"{task['task_id']}.json"
    payload = serialize_task(task)
    task_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_task_from_disk(task_id: str) -> Optional[dict]:
    """从磁盘恢复任务。"""
    if task_id in TASKS:
        return TASKS[task_id]
    task_file = TASKS_DIR / f"{task_id}.json"
    if task_file.exists():
        return json.loads(task_file.read_text(encoding="utf-8"))
    return None
