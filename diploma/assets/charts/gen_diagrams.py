"""
Рендер схематических диаграмм (Рисунки 1, 2, 3, 5) через matplotlib.
Используется как fallback к Mermaid (mmdc недоступен в окружении).
Mermaid-исходники лежат рядом в diploma/assets/diagrams/*.mmd для ручной пересборки.

Запуск:
    cd D:/model-forge && python diploma/assets/charts/gen_diagrams.py

Все PNG имеют ширину >= 1600 px (требование: избежать пикселизации в .docx).
"""
from __future__ import annotations
import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

# Палитра — нейтральная, под печать (черно-белая копия должна оставаться читаемой)
C_FE = "#E3F2FD"     # frontend (светло-голубой)
C_API = "#FFF3E0"    # api (светло-оранжевый)
C_KAFKA = "#F3E5F5"  # шина (светло-фиолетовый)
C_ML = "#E8F5E9"     # ml worker (светло-зелёный)
C_DB = "#FCE4EC"     # хранилища (светло-розовый)
C_OBS = "#ECEFF1"    # observability (серый)
C_BORDER = "#37474F"

DPI = 200  # 8" * 200 = 1600 px


def _box(ax, x, y, w, h, text, fc=C_API, ec=C_BORDER, fontsize=10, weight="normal"):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.4, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, weight=weight, wrap=True)
    return (x + w / 2, y + h / 2)


def _arrow(ax, p1, p2, label=None, style="-|>", linestyle="-",
           color=C_BORDER, rad=0.0, fontsize=8):
    arr = FancyArrowPatch(
        p1, p2, arrowstyle=style, mutation_scale=14,
        linewidth=1.2, color=color, linestyle=linestyle,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arr)
    if label:
        mx = (p1[0] + p2[0]) / 2
        my = (p1[1] + p2[1]) / 2
        ax.text(mx, my, label, fontsize=fontsize, ha="center", va="bottom",
                bbox=dict(facecolor="white", edgecolor="none", pad=1.5, alpha=0.85))


# ──────────────────────────────────────────────────────────────────────────
# Рисунок 1 – Компонентная диаграмма платформы model-forge
# ──────────────────────────────────────────────────────────────────────────
def fig1_architecture():
    fig, ax = plt.subplots(figsize=(10.5, 6.6), dpi=DPI)
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 11)
    ax.axis("off")

    # верхняя строка: FE → API
    fe = _box(ax, 0.5, 7.5, 3.0, 1.6, "React SPA\n(frontend)", fc=C_FE, weight="bold")
    api = _box(ax, 4.5, 7.5, 3.0, 1.6, "Kotlin\nSpring Boot\n(api-service)", fc=C_API, weight="bold")
    # средняя: Kafka
    kafka = _box(ax, 8.5, 7.5, 3.0, 1.6, "Apache Kafka\ntopics:\ntasks, results", fc=C_KAFKA, weight="bold")
    # справа сверху: ML
    ml = _box(ax, 12.5, 7.5, 3.5, 1.6, "Python ML Worker\n(TripoSR)", fc=C_ML, weight="bold")

    # хранилища (нижний ряд)
    pg = _box(ax, 4.5, 4.5, 3.0, 1.4, "PostgreSQL\n(tasks, users)", fc=C_DB)
    s3 = _box(ax, 8.5, 4.5, 3.0, 1.4, "MinIO (S3)\ninput/, output/", fc=C_DB)

    # observability (нижний ряд)
    loki = _box(ax, 1.0, 1.5, 2.5, 1.2, "Loki\n+ Promtail", fc=C_OBS)
    prom = _box(ax, 4.5, 1.5, 2.5, 1.2, "Prometheus", fc=C_OBS)
    graf = _box(ax, 8.5, 1.5, 2.5, 1.2, "Grafana", fc=C_OBS)

    # стрелки
    _arrow(ax, fe, api, "HTTPS / REST", fontsize=8)
    _arrow(ax, api, kafka, "produce", fontsize=8)
    _arrow(ax, kafka, ml, "consume", fontsize=8)
    _arrow(ax, ml, kafka, "results", fontsize=8, rad=-0.25)
    _arrow(ax, kafka, api, "consume\nresults", fontsize=8, rad=-0.25)
    _arrow(ax, api, pg, "JDBC", fontsize=8)
    _arrow(ax, api, s3, "S3 API", fontsize=8, rad=0.15)
    _arrow(ax, ml, s3, "S3 API", fontsize=8, rad=-0.15)
    # observability — пунктир
    _arrow(ax, api, prom, "metrics", linestyle=":", fontsize=8, rad=-0.2)
    _arrow(ax, ml, prom, "metrics", linestyle=":", fontsize=8, rad=-0.3)
    _arrow(ax, api, loki, "logs", linestyle=":", fontsize=8, rad=0.2)
    _arrow(ax, ml, loki, "logs", linestyle=":", fontsize=8, rad=0.4)
    _arrow(ax, prom, graf, fontsize=8)
    _arrow(ax, loki, graf, fontsize=8, rad=-0.15)

    # пунктирные группировки слоёв
    for x0, x1, y0, y1, lab in [
        (0.3, 3.7, 7.2, 9.3, "Клиент"),
        (4.3, 7.7, 7.2, 9.3, "API"),
        (8.3, 11.7, 7.2, 9.3, "Шина"),
        (12.3, 16.2, 7.2, 9.3, "Worker"),
        (4.3, 11.7, 4.2, 6.1, "Хранилища"),
        (0.7, 11.2, 1.2, 2.9, "Наблюдаемость"),
    ]:
        ax.add_patch(mpatches.Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            fill=False, edgecolor="#90A4AE", linestyle="--", linewidth=0.8,
        ))
        ax.text(x0 + 0.1, y1 - 0.18, lab, fontsize=7.5, color="#546E7A", style="italic")

    out = os.path.join(OUT_DIR, "architecture-overview.png")
    plt.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рисунок 2 – Sequence-диаграмма пути запроса
# ──────────────────────────────────────────────────────────────────────────
def fig2_sequence():
    actors = ["Пользователь\n(React SPA)", "Kotlin API", "MinIO (S3)",
              "PostgreSQL", "Kafka", "ML Worker"]
    fig, ax = plt.subplots(figsize=(9, 6.5), dpi=DPI)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 17)
    ax.axis("off")

    n = len(actors)
    xs = [1.5 + i * 2 for i in range(n)]
    # actor headers
    for x, a in zip(xs, actors):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 0.85, 15.5), 1.7, 0.9,
            boxstyle="round,pad=0.02", facecolor=C_API, edgecolor=C_BORDER, linewidth=1.2))
        ax.text(x, 15.95, a, ha="center", va="center", fontsize=8.5, weight="bold")
        # lifeline
        ax.plot([x, x], [0.5, 15.4], color="#90A4AE", linestyle="--", linewidth=0.7)

    # сообщения: (from_idx, to_idx, y, label, dashed?)
    msgs = [
        (0, 1, 14.4, "1. POST /api/tasks (image)", False),
        (1, 2, 13.6, "2. PUT input/{task_id}.png", False),
        (1, 3, 12.8, "3. INSERT tasks (PENDING)", False),
        (1, 4, 12.0, "4. produce tasks-topic", False),
        (1, 0, 11.2, "5. 202 Accepted, task_id", True),
        (4, 5, 10.4, "6. consume tasks-topic", False),
        (5, 2, 9.6,  "7. GET input/{task_id}.png", False),
        (5, 5, 8.8,  "8. TripoSR inference (1.8 c)", False),
        (5, 2, 8.0,  "9. PUT output/{task_id}.glb", False),
        (5, 4, 7.2,  "10. produce results-topic", False),
        (4, 1, 6.4,  "11. consume results-topic", False),
        (1, 3, 5.6,  "12. UPDATE tasks (DONE)", False),
        (0, 1, 4.6,  "13. GET /api/tasks/{id}  (poll)", False),
        (1, 3, 3.8,  "14. SELECT status, glb_uri", False),
        (1, 0, 3.0,  "15. 200 OK + presigned URL", True),
        (0, 2, 2.0,  "16. GET presigned URL", False),
        (2, 0, 1.2,  "17. GLB-файл", True),
    ]
    for fi, ti, y, lab, dashed in msgs:
        x1, x2 = xs[fi], xs[ti]
        ls = "--" if dashed else "-"
        if fi == ti:
            # self-loop
            ax.add_patch(FancyArrowPatch(
                (x1 + 0.1, y), (x1 + 0.7, y - 0.25),
                arrowstyle="-|>", mutation_scale=10, color=C_BORDER,
                connectionstyle="arc3,rad=-0.6", linewidth=1.0, linestyle=ls))
            ax.text(x1 + 0.85, y, lab, fontsize=7.5, ha="left", va="center")
        else:
            arr = FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>",
                                  mutation_scale=10, color=C_BORDER,
                                  linewidth=1.0, linestyle=ls)
            ax.add_patch(arr)
            mx = (x1 + x2) / 2
            ax.text(mx, y + 0.12, lab, fontsize=7.3, ha="center", va="bottom",
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.0, alpha=0.9))

    out = os.path.join(OUT_DIR, "sequence-request-flow.png")
    plt.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рисунок 3 – ER-диаграмма
# ──────────────────────────────────────────────────────────────────────────
def fig3_er():
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=DPI)
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 13)
    ax.axis("off")

    def entity(x, y, w, h, name, attrs):
        # header
        ax.add_patch(mpatches.Rectangle((x, y + h - 0.7), w, 0.7,
                                        facecolor=C_API, edgecolor=C_BORDER, linewidth=1.2))
        ax.text(x + w / 2, y + h - 0.35, name, ha="center", va="center",
                fontsize=10, weight="bold")
        # body
        ax.add_patch(mpatches.Rectangle((x, y), w, h - 0.7,
                                        facecolor="white", edgecolor=C_BORDER, linewidth=1.2))
        # attrs
        line_h = (h - 0.9) / max(1, len(attrs))
        for i, (col, typ, mark) in enumerate(attrs):
            ty = y + h - 0.7 - 0.2 - i * line_h
            mark_str = f"[{mark}]" if mark else ""
            ax.text(x + 0.15, ty, f"{mark_str} {col}",
                    fontsize=8.2, ha="left", va="center", weight="bold" if "PK" in (mark or "") else "normal")
            ax.text(x + w - 0.15, ty, typ, fontsize=7.8, ha="right", va="center",
                    color="#546E7A", style="italic")

    entity(0.5, 7.5, 5.0, 4.5, "USERS", [
        ("id", "uuid", "PK"),
        ("email", "text", "UK"),
        ("password_hash", "text", ""),
        ("created_at", "timestamp", ""),
    ])
    entity(7.0, 6.5, 5.0, 5.5, "TASKS", [
        ("id", "uuid", "PK"),
        ("user_id", "uuid", "FK"),
        ("status", "text", ""),
        ("input_s3_uri", "text", ""),
        ("output_s3_uri", "text", ""),
        ("created_at", "timestamp", ""),
        ("updated_at", "timestamp", ""),
    ])
    entity(13.5, 8.5, 4.2, 3.5, "GENERATION_METRICS", [
        ("task_id", "uuid", "PK,FK"),
        ("inference_time_s", "numeric", ""),
        ("chamfer_distance", "numeric", ""),
        ("model_version", "text", ""),
    ])
    entity(13.5, 3.5, 4.2, 3.8, "OUTBOX_EVENTS", [
        ("id", "uuid", "PK"),
        ("task_id", "uuid", "FK"),
        ("topic", "text", ""),
        ("payload", "jsonb", ""),
        ("published_at", "timestamp", ""),
    ])
    entity(0.5, 3.0, 5.0, 3.0, "APP_SETTINGS", [
        ("key", "text", "PK"),
        ("value", "jsonb", ""),
        ("updated_at", "timestamp", ""),
    ])

    # связи (рамки → стрелки)
    def rel(p1, p2, lab, card_l, card_r, rad=0):
        arr = FancyArrowPatch(p1, p2, arrowstyle="-", linewidth=1.2,
                              color=C_BORDER, connectionstyle=f"arc3,rad={rad}")
        ax.add_patch(arr)
        ax.text(p1[0] + 0.15, p1[1] + 0.05, card_l, fontsize=8, color="#1565C0")
        ax.text(p2[0] - 0.45, p2[1] + 0.05, card_r, fontsize=8, color="#1565C0")
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 0.1, lab, fontsize=8,
                ha="center", color="#37474F", style="italic",
                bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.85))

    rel((5.5, 9.7), (7.0, 9.5), "создаёт", "1", "N")
    rel((12.0, 10.0), (13.5, 10.5), "имеет", "1", "1")
    rel((12.0, 7.5), (13.5, 5.5), "порождает", "1", "N", rad=-0.15)

    out = os.path.join(OUT_DIR, "er-diagram.png")
    plt.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рисунок 5 – ML Worker pipeline (10 стадий)
# ──────────────────────────────────────────────────────────────────────────
def fig5_ml_pipeline():
    fig, ax = plt.subplots(figsize=(10.5, 9.5), dpi=DPI)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 22)
    ax.axis("off")

    stages = [
        ("1. Consume tasks-topic", "Kafka consumer"),
        ("2. Валидация payload", "pydantic-схема"),
        ("3. UPDATE tasks", "status = PROCESSING"),
        ("4. Скачивание input", "MinIO S3 GET"),
        ("5. Препроцессинг", "resize 512×512, RGB"),
        ("6. Инференс TripoSR", "GPU float16, ~1.8 с"),
        ("7. Постпроцессинг", "extract mesh → GLB"),
        ("8. Загрузка GLB", "MinIO S3 PUT"),
        ("9. INSERT generation_metrics", "inference_time, chamfer"),
        ("10. Produce results-topic", "{task_id, status=DONE}"),
    ]

    # колонка боксов сверху вниз
    h = 1.5
    gap = 0.5
    y_top = 21.0
    centers = []
    for i, (head, sub) in enumerate(stages):
        y = y_top - i * (h + gap)
        ax.add_patch(FancyBboxPatch((2.5, y - h), 5.0, h,
                                     boxstyle="round,pad=0.02,rounding_size=0.1",
                                     facecolor=C_ML, edgecolor=C_BORDER, linewidth=1.3))
        ax.text(5.0, y - 0.45, head, ha="center", va="center",
                fontsize=10, weight="bold")
        ax.text(5.0, y - 1.05, sub, ha="center", va="center",
                fontsize=8.5, color="#37474F", style="italic")
        centers.append((5.0, y - h / 2))

    # стрелки между боксами
    for c1, c2 in zip(centers, centers[1:]):
        ax.add_patch(FancyArrowPatch((c1[0], c1[1] - h / 2),
                                      (c2[0], c2[1] + h / 2),
                                      arrowstyle="-|>", mutation_scale=12,
                                      color=C_BORDER, linewidth=1.2))

    # error sink справа
    err_y = (centers[3][1] + centers[7][1]) / 2
    ax.add_patch(FancyBboxPatch((8.5, err_y - 1.5), 3.2, 3.0,
                                 boxstyle="round,pad=0.02,rounding_size=0.1",
                                 facecolor="#FFEBEE", edgecolor="#C62828", linewidth=1.3))
    ax.text(10.1, err_y + 0.65, "Обработка\nисключений:", ha="center", va="center",
            fontsize=9.5, weight="bold")
    ax.text(10.1, err_y - 0.5, "UPDATE status=FAILED\nproduce results с error",
            ha="center", va="center", fontsize=8.2, style="italic")

    for idx, lbl in [(3, "S3 GET err"), (5, "CUDA OOM"), (7, "S3 PUT err")]:
        c = centers[idx]
        ax.add_patch(FancyArrowPatch((c[0] + 2.5, c[1]), (8.5, err_y),
                                      arrowstyle="-|>", mutation_scale=10,
                                      color="#C62828", linestyle=":", linewidth=1.0))

    out = os.path.join(OUT_DIR, "ml-worker-pipeline.png")
    plt.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


if __name__ == "__main__":
    for fn in (fig1_architecture, fig2_sequence, fig3_er, fig5_ml_pipeline):
        path = fn()
        print(f"OK: {path}")
