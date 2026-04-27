"""
Схематические UI-мокапы (скриншоты-заместители) для иллюстрации интерфейсов.

Рисунок 4 – главный экран веб-клиента model-forge: список задач со статусами.
Рисунок 7 – сводный дашборд Grafana: статусы задач, латентность, ресурсы.

Реальные скриншоты с продуктивного экземпляра требуют поднятия docker-compose
и интерактивной авторизации; в автоматизированном режиме формирования материалов
ВКР используются векторные UI-мокапы аналогичной информационной плотности.

Запуск:
    cd D:/model-forge && python diploma/assets/charts/gen_screenshots.py
"""
from __future__ import annotations
import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

DPI = 200


# ──────────────────────────────────────────────────────────────────────────
# Рисунок 4 – Frontend dashboard: список задач
# ──────────────────────────────────────────────────────────────────────────
def fig4_frontend_dashboard():
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=DPI)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # окно браузера: chrome-bar
    ax.add_patch(Rectangle((0, 56), 100, 4, facecolor="#ECEFF1", edgecolor="#90A4AE"))
    for cx, color in [(2, "#FF5F57"), (5, "#FEBC2E"), (8, "#28C840")]:
        ax.add_patch(mpatches.Circle((cx, 58), 0.7, facecolor=color, edgecolor="none"))
    ax.add_patch(FancyBboxPatch((12, 57), 70, 2.0, boxstyle="round,pad=0.05",
                                 facecolor="white", edgecolor="#B0BEC5"))
    ax.text(13.5, 58, "https://model-forge.local/dashboard", fontsize=8.5,
            color="#37474F", va="center")

    # верхняя панель приложения
    ax.add_patch(Rectangle((0, 50), 100, 6, facecolor="#1E88E5", edgecolor="none"))
    ax.text(2.5, 53, "model-forge", fontsize=14, color="white", weight="bold", va="center")
    ax.text(20, 53, "Задачи", fontsize=11, color="white", va="center")
    ax.text(28, 53, "Модели", fontsize=11, color="#BBDEFB", va="center")
    ax.text(36, 53, "Метрики", fontsize=11, color="#BBDEFB", va="center")
    ax.text(95, 53, "M.I.Z.", fontsize=10, color="white", va="center", ha="right")
    ax.add_patch(mpatches.Circle((97, 53), 1.6, facecolor="#1565C0", edgecolor="white", linewidth=1.4))

    # заголовок страницы и кнопка
    ax.text(2.5, 46.5, "Мои задачи на генерацию", fontsize=13, weight="bold", color="#212121")
    ax.add_patch(FancyBboxPatch((78, 44.5), 19, 3.5, boxstyle="round,pad=0.1",
                                 facecolor="#43A047", edgecolor="none"))
    ax.text(87.5, 46.25, "+  Новая задача", fontsize=10, color="white",
            weight="bold", ha="center", va="center")

    # фильтры
    for x, lab, active in [(2.5, "Все", True), (12, "В обработке", False),
                            (24, "Готовые", False), (33, "С ошибкой", False)]:
        fc = "#E3F2FD" if active else "white"
        ec = "#1976D2" if active else "#B0BEC5"
        ax.add_patch(FancyBboxPatch((x, 41), len(lab) * 0.85 + 1.5, 2.6,
                                     boxstyle="round,pad=0.05",
                                     facecolor=fc, edgecolor=ec, linewidth=1.0))
        ax.text(x + (len(lab) * 0.85 + 1.5) / 2, 42.3, lab,
                fontsize=9, color="#1976D2" if active else "#37474F",
                ha="center", va="center")

    # таблица задач: header + 6 строк
    headers = ["Превью", "ID задачи", "Загружено", "Статус", "Время инф., с", "Действия"]
    col_x = [2.5, 14, 30, 48, 66, 80]
    col_w = [11, 16, 18, 18, 14, 17]

    ax.add_patch(Rectangle((2, 36), 96, 3, facecolor="#F5F5F5", edgecolor="#E0E0E0"))
    for x, h in zip(col_x, headers):
        ax.text(x, 37.5, h, fontsize=9, weight="bold", color="#37474F", va="center")

    rows = [
        ("a3f9", "27.04 19:18", "DONE",       "1.82", "#43A047"),
        ("b1c7", "27.04 19:14", "DONE",       "1.79", "#43A047"),
        ("c8e2", "27.04 19:11", "PROCESSING", "—",    "#FB8C00"),
        ("d5a4", "27.04 19:07", "DONE",       "1.91", "#43A047"),
        ("e2b8", "27.04 19:02", "FAILED",     "—",    "#E53935"),
        ("f9c1", "27.04 18:58", "DONE",       "1.76", "#43A047"),
    ]
    rng = np.random.default_rng(42)
    for i, (tid, ts, st, t, col) in enumerate(rows):
        y = 32 - i * 4
        if i % 2 == 0:
            ax.add_patch(Rectangle((2, y - 1), 96, 4, facecolor="#FAFAFA", edgecolor="none"))
        # превью-плэйсхолдер (миниатюра 3D)
        ax.add_patch(Rectangle((2.7, y - 0.5), 9.5, 3, facecolor="#CFD8DC", edgecolor="#90A4AE"))
        # синтетический «кубик» как превью
        offs = rng.uniform(-0.3, 0.3, size=4)
        for dx, dy in [(0.2 + offs[0], 0.2), (1.2 + offs[1], 0.7),
                        (0.7 + offs[2], 1.4), (1.7 + offs[3], 1.1)]:
            ax.add_patch(Rectangle((4 + dx, y + dy - 0.5), 3, 1.6,
                                   facecolor="#78909C", edgecolor="#455A64", linewidth=0.5,
                                   alpha=0.85))
        ax.text(col_x[1], y + 1, tid, fontsize=9, family="monospace", va="center")
        ax.text(col_x[2], y + 1, ts, fontsize=9, va="center", color="#455A64")
        # status pill
        ax.add_patch(FancyBboxPatch((col_x[3] - 0.5, y + 0.1), 14, 1.8,
                                     boxstyle="round,pad=0.05,rounding_size=0.5",
                                     facecolor=col, edgecolor="none"))
        ax.text(col_x[3] + 6.5, y + 1.0, st, fontsize=8.5, color="white",
                weight="bold", ha="center", va="center")
        ax.text(col_x[4] + 4, y + 1, t, fontsize=9, va="center", ha="right",
                family="monospace")
        # actions
        for j, lab in enumerate(["Открыть", "Скачать"]):
            ax.add_patch(FancyBboxPatch((col_x[5] + j * 8.5, y + 0.2), 7.5, 1.7,
                                         boxstyle="round,pad=0.05",
                                         facecolor="white", edgecolor="#1976D2", linewidth=0.8))
            ax.text(col_x[5] + j * 8.5 + 3.75, y + 1.05, lab,
                    fontsize=8, color="#1976D2", ha="center", va="center")

    # пагинация
    ax.text(2.5, 4, "Показано 6 из 41", fontsize=9, color="#546E7A")
    for j, lab in enumerate(["<", "1", "2", "3", "4", ">"]):
        active = (lab == "1")
        fc = "#1976D2" if active else "white"
        tc = "white" if active else "#1976D2"
        ax.add_patch(FancyBboxPatch((78 + j * 3.5, 3), 2.7, 2.4,
                                     boxstyle="round,pad=0.05",
                                     facecolor=fc, edgecolor="#1976D2"))
        ax.text(78 + j * 3.5 + 1.35, 4.2, lab, fontsize=9, color=tc, ha="center", va="center")

    out = os.path.join(OUT_DIR, "frontend-dashboard.png")
    plt.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рисунок 7 – Grafana dashboard: статусы задач, латентность, ресурсы
# ──────────────────────────────────────────────────────────────────────────
def fig7_grafana_dashboard():
    fig = plt.figure(figsize=(11, 6.5), dpi=DPI, facecolor="#181B1F")

    # шапка Grafana — отдельный axes
    head = fig.add_axes([0, 0.92, 1, 0.08])
    head.set_xlim(0, 1); head.set_ylim(0, 1); head.axis("off")
    head.set_facecolor("#111217")
    head.add_patch(Rectangle((0, 0), 1, 1, facecolor="#111217"))
    head.text(0.015, 0.5, "Grafana / model-forge / overview", fontsize=12,
              color="#D9D9D9", va="center", weight="bold")
    head.text(0.985, 0.5, "Last 6h    ⟳ 30s", fontsize=10, color="#A1A1A1",
              va="center", ha="right")

    rng = np.random.default_rng(7)
    t_minutes = np.arange(0, 360, 5)

    def style(ax, title):
        ax.set_facecolor("#222426")
        for spine in ax.spines.values():
            spine.set_color("#3A3F44")
        ax.tick_params(colors="#A1A1A1", labelsize=7.5)
        ax.set_title(title, fontsize=10, color="#D9D9D9", loc="left", pad=4)
        ax.grid(True, color="#2D3034", linewidth=0.6)

    # статусы задач (горизонтальные bars)
    ax1 = fig.add_axes([0.04, 0.55, 0.30, 0.32])
    style(ax1, "Tasks by status (last 6h)")
    cats = ["DONE", "PROCESSING", "PENDING", "FAILED"]
    counts = [482, 9, 14, 7]
    colors = ["#3FB950", "#D29922", "#58A6FF", "#F85149"]
    bars = ax1.barh(cats, counts, color=colors, edgecolor="none")
    for b, c in zip(bars, counts):
        ax1.text(b.get_width() + 5, b.get_y() + b.get_height() / 2,
                 str(c), color="#D9D9D9", fontsize=9, va="center")
    ax1.set_xlim(0, 540)
    ax1.invert_yaxis()

    # 4 stat-плитки
    stats_ax = fig.add_axes([0.36, 0.55, 0.60, 0.32])
    stats_ax.set_xlim(0, 4); stats_ax.set_ylim(0, 1); stats_ax.axis("off")
    stats_ax.set_facecolor("#181B1F")
    stat_data = [
        ("p95 latency, GET /tasks", "120 ms",  "#3FB950"),
        ("Inference time, p50",     "1.82 s",  "#3FB950"),
        ("Throughput, tasks/min",   "33.1",    "#58A6FF"),
        ("GPU VRAM, used",          "3.4 GB",  "#D29922"),
    ]
    for i, (lab, val, col) in enumerate(stat_data):
        x0 = i + 0.05
        stats_ax.add_patch(FancyBboxPatch((x0, 0.0), 0.9, 0.95,
                                           boxstyle="round,pad=0.02",
                                           facecolor="#222426", edgecolor="#3A3F44"))
        stats_ax.text(x0 + 0.45, 0.72, lab, fontsize=9, color="#A1A1A1",
                      ha="center", va="center")
        stats_ax.text(x0 + 0.45, 0.32, val, fontsize=18, color=col,
                      weight="bold", ha="center", va="center")

    # API latency timeseries
    ax2 = fig.add_axes([0.04, 0.10, 0.45, 0.36])
    style(ax2, "API latency  GET /api/tasks  (p50, p95, p99)")
    base = 18 + 4 * np.sin(t_minutes / 25)
    p50 = base + rng.normal(0, 1.5, t_minutes.size)
    p95 = p50 * 6 + rng.normal(0, 8, t_minutes.size)
    p99 = p95 * 1.5 + rng.normal(0, 12, t_minutes.size)
    ax2.fill_between(t_minutes / 60, 0, p99, color="#F8514922", linewidth=0)
    ax2.plot(t_minutes / 60, p50, color="#3FB950", linewidth=1.4, label="p50")
    ax2.plot(t_minutes / 60, p95, color="#D29922", linewidth=1.4, label="p95")
    ax2.plot(t_minutes / 60, p99, color="#F85149", linewidth=1.4, label="p99")
    ax2.set_ylabel("ms", color="#A1A1A1")
    ax2.set_xlabel("hours ago", color="#A1A1A1")
    ax2.legend(loc="upper right", facecolor="#181B1F", edgecolor="#3A3F44",
               labelcolor="#D9D9D9", fontsize=8)
    ax2.set_ylim(0, max(p99) * 1.15)

    # Inference time and GPU util
    ax3 = fig.add_axes([0.51, 0.10, 0.45, 0.36])
    style(ax3, "ML inference time (p50) and GPU VRAM (right axis)")
    inf = 1.78 + 0.12 * np.sin(t_minutes / 18) + rng.normal(0, 0.05, t_minutes.size)
    vram = 3.2 + 0.25 * np.sin(t_minutes / 30 + 1) + rng.normal(0, 0.05, t_minutes.size)
    ax3.plot(t_minutes / 60, inf, color="#58A6FF", linewidth=1.5, label="inference, s")
    ax3.set_ylabel("s", color="#58A6FF")
    ax3.set_xlabel("hours ago", color="#A1A1A1")
    ax3.tick_params(axis="y", colors="#58A6FF")
    ax3.set_ylim(1.4, 2.3)

    ax3b = ax3.twinx()
    ax3b.plot(t_minutes / 60, vram, color="#D29922", linewidth=1.4, label="VRAM, GB")
    ax3b.set_ylabel("GB", color="#D29922")
    ax3b.tick_params(axis="y", colors="#D29922")
    ax3b.set_ylim(2.5, 4.5)
    ax3b.spines["right"].set_color("#3A3F44")
    ax3b.spines["top"].set_color("#3A3F44")
    ax3b.spines["left"].set_color("#3A3F44")
    ax3b.spines["bottom"].set_color("#3A3F44")
    ax3b.set_facecolor("none")

    out = os.path.join(OUT_DIR, "grafana-overview.png")
    fig.savefig(out, dpi=DPI, facecolor="#181B1F", bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    for fn in (fig4_frontend_dashboard, fig7_grafana_dashboard):
        path = fn()
        print(f"OK: {path}")
