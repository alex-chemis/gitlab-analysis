from pathlib import Path
from typing import List, Sequence, Optional
import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import colorsys
import random


def ensure_parent_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def unique_colors(n: int, seed: Optional[int] = None) -> list[tuple[float, float, float]]:
    """
    Генерирует n уникальных «приятных» цветов.
    Алгоритм: равномерный обход оттенков (golden ratio) + лёгкая случайность насыщенности.
    Если задан seed — палитра будет воспроизводимой.
    """
    rng = random.Random(seed)
    h = rng.random()
    phi = 0.6180339887498949  # golden ratio conjugate
    colors: list[tuple[float, float, float]] = []
    for _ in range(n):
        h = (h + phi) % 1.0
        s = 0.60 + 0.25 * rng.random()  # 0.60..0.85
        v = 0.90  # яркость
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        colors.append((r, g, b))
    return colors


def bar_chart(labels: Sequence[str], values: Sequence[float], out_path: str | Path, title: str = "", xlabel: str = "", ylabel: str = "", rotate_x: int = 45) -> Path:
    out_p = ensure_parent_dir(out_path)
    fig = plt.figure(figsize=(12, 6))
    plt.bar(labels, values)
    plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    if rotate_x:
        plt.xticks(rotation=rotate_x, ha="right")
    plt.tight_layout()
    fig.savefig(out_p, dpi=130)
    plt.close(fig)
    return out_p


def barh_chart(labels: Sequence[str], values: Sequence[float], out_path: str | Path, title: str = "", xlabel: str = "", ylabel: str = "") -> Path:
    out_p = ensure_parent_dir(out_path)
    fig = plt.figure(figsize=(12, 0.5 * max(6, len(labels))))
    plt.barh(labels, values)
    plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    plt.tight_layout()
    fig.savefig(out_p, dpi=130)
    plt.close(fig)
    return out_p


def pie_chart(labels: Sequence[str], values: Sequence[float], out_path: str | Path, title: str = "", random_colors: bool = False, seed: Optional[int] = None) -> Path:
    out_p = ensure_parent_dir(out_path)
    if not labels or not values or sum(values) <= 0:
        raise ValueError("pie_chart: empty labels/values or zero sum")
    fig = plt.figure(figsize=(10, 10))
    colors = unique_colors(len(labels), seed) if random_colors else None

    def _fmt(pct, allvals):
        total = int(sum(allvals))
        count = int(round(pct / 100.0 * total))
        return f"{pct:.1f}%\n({count})"

    wedges, texts, autotexts = plt.pie(values, autopct=lambda p: _fmt(p, values), startangle=90, colors=colors, pctdistance=1.12)
    plt.title(title)
    # если языков много — легенда сбоку
    plt.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=9)
    plt.tight_layout()
    fig.savefig(out_p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out_p
