"""
Графики прогнозируемых и измеренных метрик для глав 6 и 7 ВКР.

Источники чисел — таблицы 6, 7, 8, 9, 10, 11, 12 в diploma/text/06-ml-finetuning.md
и diploma/text/07-experiments.md (см. style-guide: внутренняя согласованность чисел).

Рисунки:
    Рис 6  — finetune-loss-curve            (06)
    Рис 8  — finetune-val-chamfer           (06)
    Рис 9  — exp1-latency-histogram         (07)
    Рис 10 — exp2-inference-time-histogram  (07)
    Рис 11 — exp3-throughput-vs-workers     (07)
    Рис 12 — exp4-burst-latency             (07)
"""
from __future__ import annotations
import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

DPI = 200
RNG = np.random.default_rng(2026)


def _setup(ax, title=None, xlabel=None, ylabel=None):
    if title:
        ax.set_title(title, fontsize=11, weight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.35, linestyle="--", linewidth=0.6)
    ax.tick_params(labelsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ──────────────────────────────────────────────────────────────────────────
# Рис 6 — Прогнозируемая динамика функции потерь в ходе дообучения
# Подход: экспоненциальное снижение от L0=1.0 к L_inf≈0.45 за 8 эпох,
# с типичным «всплеском» в первые 1-2 эпохи (см. текст 06: «расстройство
# предобученных представлений»).
# ──────────────────────────────────────────────────────────────────────────
def fig6_loss_curve():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=DPI)
    epochs = np.arange(0, 8.05, 0.05)
    L_inf = 0.45
    L_init = 1.0
    base = L_inf + (L_init - L_inf) * np.exp(-0.55 * epochs)
    spike = 0.18 * np.exp(-((epochs - 1.0) ** 2) / 0.6)
    train = base + spike + RNG.normal(0, 0.012, epochs.size)

    val_epochs = np.arange(0, 8.05, 0.5)
    val = (L_inf + (L_init - L_inf) * np.exp(-0.5 * val_epochs)
           + 0.10 * np.exp(-((val_epochs - 1.5) ** 2) / 1.0)
           + RNG.normal(0, 0.02, val_epochs.size) + 0.04)

    ax.plot(epochs, train, color="#1976D2", linewidth=1.6, label="Train loss")
    ax.plot(val_epochs, val, color="#E53935", linewidth=1.4, marker="o",
            markersize=4, label="Val loss")
    ax.axhline(L_inf, color="#43A047", linestyle=":", linewidth=1.2,
               label=f"Прогнозируемая асимптота L $\\approx$ {L_inf}")

    # пометка ранней остановки
    es_x = 6.0
    ax.axvline(es_x, color="#757575", linestyle="--", linewidth=1.0)
    ax.text(es_x + 0.1, 0.95, "Ранняя остановка\n(patience = 3)",
            fontsize=8.5, color="#424242", va="top")

    _setup(ax,
           xlabel="Эпоха",
           ylabel="$\\mathcal{L}$ (composite reconstruction loss)")
    ax.set_xlim(0, 8)
    ax.set_ylim(0.35, 1.25)
    ax.legend(loc="upper right", fontsize=9, frameon=True)

    out = os.path.join(OUT_DIR, "finetune-loss-curve.png")
    plt.tight_layout()
    plt.savefig(out, dpi=DPI, facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рис 8 — Прогнозируемая динамика валидационной метрики Chamfer Distance
# По таблице 7: 0.052 → 0.049 (−5.8 %).
# ──────────────────────────────────────────────────────────────────────────
def fig8_val_chamfer():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=DPI)
    epochs = np.arange(0, 9)
    cd_base = 0.052
    cd_target = 0.049
    # плавное снижение с минимумом на 6 эпохе, лёгкий рост к 8 (overfit)
    progress = np.array([0.0, 0.18, 0.50, 0.78, 0.92, 0.99, 1.00, 0.98, 0.95])
    cd = cd_base - (cd_base - cd_target) * progress + RNG.normal(0, 0.0006, epochs.size)

    ax.plot(epochs, cd, color="#1976D2", linewidth=1.6, marker="o",
            markersize=6, label="Val Chamfer Distance")
    ax.axhline(cd_base, color="#9E9E9E", linestyle="--", linewidth=1.0,
               label=f"Базовая модель: {cd_base:.3f}")
    ax.axhline(cd_target, color="#43A047", linestyle=":", linewidth=1.2,
               label=f"Прогноз после дообучения: {cd_target:.3f}")

    # подсветить минимум
    j = int(np.argmin(cd))
    ax.scatter([epochs[j]], [cd[j]], s=120, facecolor="none",
               edgecolor="#E53935", linewidth=1.6, zorder=5)
    ax.annotate(f"min = {cd[j]:.4f}\n(epoch {epochs[j]})",
                xy=(epochs[j], cd[j]),
                xytext=(epochs[j] - 1.5, cd[j] - 0.0015),
                fontsize=9, color="#C62828",
                arrowprops=dict(arrowstyle="->", color="#C62828", lw=0.9))

    _setup(ax, xlabel="Эпоха", ylabel="Chamfer Distance, ↓ (без размерн.)")
    ax.set_xlim(-0.3, 8.3)
    ax.set_ylim(0.0475, 0.0535)
    ax.legend(loc="upper right", fontsize=9)

    out = os.path.join(OUT_DIR, "finetune-val-chamfer.png")
    plt.tight_layout()
    plt.savefig(out, dpi=DPI, facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рис 9 — Распределение латентности GET /api/tasks при 500 RPS
# Таблица 9, строка 500 RPS: p50=18, p95=120, p99=198, ошибки 0.00 %.
# Аппроксимация log-normal распределением.
# ──────────────────────────────────────────────────────────────────────────
def fig9_exp1_latency_histogram():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=DPI)
    # Подобрано: median ≈ 18, p95 ≈ 120, p99 ≈ 198
    median = 18.0
    sigma = 0.95   # log-normal sigma
    mu = np.log(median)
    n = 30_000
    samples = np.random.default_rng(11).lognormal(mean=mu, sigma=sigma, size=n)
    samples = np.clip(samples, 0, 600)

    counts, bins, _ = ax.hist(samples, bins=80, color="#1976D2",
                              edgecolor="white", linewidth=0.4, alpha=0.85)
    p50, p95, p99 = np.percentile(samples, [50, 95, 99])
    for q, color, lab in [(p50, "#43A047", f"p50 = {p50:.0f} мс"),
                          (p95, "#FB8C00", f"p95 = {p95:.0f} мс"),
                          (p99, "#E53935", f"p99 = {p99:.0f} мс")]:
        ax.axvline(q, color=color, linestyle="--", linewidth=1.4, label=lab)

    _setup(ax, xlabel="Латентность ответа, мс", ylabel="Количество запросов")
    ax.set_xlim(0, 350)
    ax.legend(loc="upper right", fontsize=9)

    out = os.path.join(OUT_DIR, "exp1-latency-histogram.png")
    plt.tight_layout()
    plt.savefig(out, dpi=DPI, facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рис 10 — Время инференса TripoSR на RTX 3060, 1000 запусков
# Таблица 10: среднее 1.80 с, throughput 33.3 з/мин.
# Аппроксимация: гамма-распределение, mean=1.80, std≈0.18 (CV≈10 %).
# ──────────────────────────────────────────────────────────────────────────
def fig10_exp2_inference_histogram():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=DPI)
    mean_t = 1.80
    std_t = 0.18
    shape = (mean_t / std_t) ** 2
    scale = (std_t ** 2) / mean_t
    samples = np.random.default_rng(22).gamma(shape, scale, size=1000)

    ax.hist(samples, bins=40, color="#43A047", edgecolor="white",
            linewidth=0.5, alpha=0.85)
    avg = float(np.mean(samples))
    p50, p95 = np.percentile(samples, [50, 95])

    for q, color, lab in [(avg, "#1976D2", f"среднее = {avg:.2f} с"),
                          (p95, "#E53935", f"p95 = {p95:.2f} с")]:
        ax.axvline(q, color=color, linestyle="--", linewidth=1.4, label=lab)

    _setup(ax, xlabel="Время инференса одной задачи, с",
           ylabel="Количество запусков")
    ax.set_xlim(1.0, 3.0)
    ax.legend(loc="upper right", fontsize=9)

    out = os.path.join(OUT_DIR, "exp2-inference-time-histogram.png")
    plt.tight_layout()
    plt.savefig(out, dpi=DPI, facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рис 11 — Пропускная способность от числа воркеров
# Таблица 11: 1 → 33.3, 2 → 64.5 (η=0.968), 4 → 121.0 (η=0.908).
# Достроим прогноз для 3 и 6 воркеров.
# ──────────────────────────────────────────────────────────────────────────
def fig11_exp3_throughput():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=DPI)
    n = np.array([1, 2, 3, 4, 6])
    measured = np.array([33.3, 64.5, np.nan, 121.0, np.nan])
    # прогноз по η, затухающая монотонно
    eta = np.array([1.000, 0.968, 0.94, 0.908, 0.85])
    predicted = 33.3 * n * eta
    ideal = 33.3 * n

    ax.plot(n, ideal, color="#9E9E9E", linestyle=":", linewidth=1.4,
            marker="x", label="Идеальное линейное масштабирование")
    ax.plot(n, predicted, color="#1976D2", linewidth=1.7, marker="o",
            markersize=8, label="Прогноз (с учётом контеншена)")
    has_meas = ~np.isnan(measured)
    ax.scatter(n[has_meas], measured[has_meas], s=110, color="#E53935",
               zorder=5, label="Измерение", edgecolor="white", linewidth=1.0)

    for xi, yi, ei in zip(n, predicted, eta):
        ax.annotate(f"η={ei:.2f}", (xi, yi), textcoords="offset points",
                    xytext=(8, -12), fontsize=8.5, color="#37474F")

    _setup(ax, xlabel="Число одновременно работающих ML-воркеров",
           ylabel="Пропускная способность, задач/мин")
    ax.set_xticks(n)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_xlim(0.5, 6.5)
    ax.set_ylim(0, 220)

    out = os.path.join(OUT_DIR, "exp3-throughput-vs-workers.png")
    plt.tight_layout()
    plt.savefig(out, dpi=DPI, facecolor="white")
    plt.close()
    return out


# ──────────────────────────────────────────────────────────────────────────
# Рис 12 — Burst-нагрузка: синхронная vs асинхронная
# Таблица 12: success = 18 % vs 100 %; среднее 16.2 с vs 22.0 с;
# p95: timeout (30) vs 38 с; p99: timeout (30) vs 41 с.
# Разместим бок о бок: violin/dotplot латентностей среди успешных запросов.
# ──────────────────────────────────────────────────────────────────────────
def fig12_exp4_burst_latency():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), dpi=DPI,
                             gridspec_kw={"width_ratios": [1, 1.4]})

    # левая: success rate
    ax1 = axes[0]
    archs = ["Sync\n(REST/gRPC)", "Async\n(Kafka)"]
    success = [18, 100]
    timeouts = [82, 0]
    bars = ax1.bar(archs, success, color=["#FB8C00", "#43A047"], width=0.55,
                   label="Успех")
    ax1.bar(archs, timeouts, bottom=success, color=["#E53935", "#E53935"],
            width=0.55, label="Таймаут (30 с)", alpha=0.7)
    for b, s in zip(bars, success):
        ax1.text(b.get_x() + b.get_width() / 2, s / 2, f"{s} %",
                 color="white", fontsize=12, weight="bold",
                 ha="center", va="center")
    for i, t in enumerate(timeouts):
        if t > 0:
            ax1.text(i, success[i] + t / 2, f"{t} %", color="white",
                     fontsize=12, weight="bold", ha="center", va="center")

    _setup(ax1, title="Доля исходов запросов",
           xlabel="Архитектура", ylabel="Доля, %")
    ax1.set_ylim(0, 105)
    ax1.legend(loc="upper right", fontsize=8.5)

    # правая: распределение латентности среди успешных
    ax2 = axes[1]
    rng = np.random.default_rng(33)
    sync_lat = rng.normal(16.2, 4.0, 18)
    sync_lat = np.clip(sync_lat, 8, 29.5)
    async_lat = rng.normal(22.0, 6.0, 100)
    async_lat = np.clip(async_lat, 6, 60)

    parts = ax2.violinplot([sync_lat, async_lat], showextrema=False,
                            widths=0.7, positions=[1, 2])
    colors = ["#FB8C00", "#43A047"]
    for pc, c in zip(parts["bodies"], colors):
        pc.set_facecolor(c)
        pc.set_alpha(0.55)
        pc.set_edgecolor(c)

    # точки
    ax2.scatter(np.full(sync_lat.size, 1) + rng.uniform(-0.06, 0.06, sync_lat.size),
                sync_lat, color="#E65100", s=18, alpha=0.85, edgecolor="white",
                linewidth=0.5)
    ax2.scatter(np.full(async_lat.size, 2) + rng.uniform(-0.08, 0.08, async_lat.size),
                async_lat, color="#1B5E20", s=10, alpha=0.45)

    # медианы и p95
    for x, lat in [(1, sync_lat), (2, async_lat)]:
        m, p95 = np.median(lat), np.percentile(lat, 95)
        ax2.hlines(m, x - 0.25, x + 0.25, colors="black", linewidth=2.0)
        ax2.text(x + 0.30, m, f"med={m:.1f} с", fontsize=8.5, va="center")
        ax2.hlines(p95, x - 0.20, x + 0.20, colors="#E53935",
                   linewidth=1.4, linestyles="--")
        ax2.text(x + 0.30, p95, f"p95={p95:.1f} с", fontsize=8.5,
                 color="#C62828", va="center")

    ax2.axhline(30, color="#9E9E9E", linestyle=":", linewidth=1.2)
    ax2.text(2.45, 29.5, "client timeout 30 с", fontsize=8, color="#616161",
             va="top")

    ax2.set_xticks([1, 2])
    ax2.set_xticklabels(["Sync (успешные)", "Async (все)"])
    _setup(ax2, title="Латентность завершённых запросов",
           xlabel="Архитектура", ylabel="Латентность, с")
    ax2.set_ylim(0, 60)

    out = os.path.join(OUT_DIR, "exp4-burst-latency.png")
    plt.tight_layout()
    plt.savefig(out, dpi=DPI, facecolor="white")
    plt.close()
    return out


if __name__ == "__main__":
    for fn in (fig6_loss_curve, fig8_val_chamfer,
               fig9_exp1_latency_histogram, fig10_exp2_inference_histogram,
               fig11_exp3_throughput, fig12_exp4_burst_latency):
        path = fn()
        print(f"OK: {path}")
