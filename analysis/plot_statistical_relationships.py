from __future__ import annotations

import argparse
import csv
import html
import math
from pathlib import Path

import numpy as np
from scipy import stats


DEFAULT_PAIRS = (
    (
        "mean_von_neumann_entropy",
        "spectral_entropy_mean",
        "local entropy vs spectral entropy",
    ),
    (
        "central_cut_entanglement_entropy_normalized",
        "spectral_entropy_mean",
        "central-cut entropy vs spectral entropy",
    ),
    (
        "total_mutual_information",
        "duration_sec",
        "total MI vs duration",
    ),
    (
        "total_mutual_information",
        "spectral_flux_mean",
        "total MI vs spectral flux",
    ),
    (
        "mean_bloch_radius",
        "rms_joint",
        "Bloch radius vs RMS",
    ),
    (
        "positive_edge_density",
        "stereo_correlation",
        "MI edge density vs stereo correlation",
    ),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def join_layer_audio(
    layer_rows: list[dict[str, str]],
    audio_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    layer_by_key = {
        (row["seed"], row["layer"]): row
        for row in layer_rows
    }
    merged: list[dict[str, str]] = []
    for audio in audio_rows:
        key = (audio["seed"], audio["layer"])
        if key not in layer_by_key:
            continue
        merged.append({**layer_by_key[key], **audio})
    return merged


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def finite_xy(
    rows: list[dict[str, str]],
    x_field: str,
    y_field: str,
) -> tuple[np.ndarray, np.ndarray]:
    pairs = [
        (to_float(row.get(x_field, "")), to_float(row.get(y_field, "")))
        for row in rows
    ]
    finite = [(x, y) for x, y in pairs if math.isfinite(x) and math.isfinite(y)]
    if not finite:
        return np.array([]), np.array([])
    x, y = zip(*finite)
    return np.asarray(x, dtype=float), np.asarray(y, dtype=float)


def correlation_rows(
    rows: list[dict[str, str]],
    pairs: tuple[tuple[str, str, str], ...],
) -> list[dict[str, object]]:
    modes = ["all", *sorted({row["mode"] for row in rows})]
    results: list[dict[str, object]] = []
    for x_field, y_field, label in pairs:
        for mode in modes:
            subset = rows if mode == "all" else [
                row for row in rows if row["mode"] == mode
            ]
            x, y = finite_xy(subset, x_field, y_field)
            result: dict[str, object] = {
                "relationship": label,
                "mode": mode,
                "x": x_field,
                "y": y_field,
                "n": int(len(x)),
                "pearson_r": "",
                "pearson_p": "",
                "spearman_rho": "",
                "spearman_p": "",
            }
            if len(x) >= 3 and np.std(x) > 0 and np.std(y) > 0:
                pearson = stats.pearsonr(x, y)
                spearman = stats.spearmanr(x, y)
                result.update(
                    {
                        "pearson_r": round(float(pearson.statistic), 6),
                        "pearson_p": f"{float(pearson.pvalue):.6g}",
                        "spearman_rho": round(float(spearman.statistic), 6),
                        "spearman_p": f"{float(spearman.pvalue):.6g}",
                    }
                )
            results.append(result)
    return results


def scale(values: np.ndarray, low: float, high: float, invert: bool = False) -> np.ndarray:
    min_value = float(np.min(values))
    max_value = float(np.max(values))
    if math.isclose(min_value, max_value):
        return np.full_like(values, (low + high) / 2, dtype=float)
    scaled = low + (values - min_value) * (high - low) / (max_value - min_value)
    return high + low - scaled if invert else scaled


def write_scatter_svg(
    path: Path,
    rows: list[dict[str, str]],
    x_field: str,
    y_field: str,
    title: str,
) -> None:
    width, height = 860, 560
    left, right, top, bottom = 90, 36, 58, 78
    plot_w = width - left - right
    plot_h = height - top - bottom
    palette = {"bfs": "#2563eb", "dfs": "#dc2626"}

    points = []
    for row in rows:
        x = to_float(row.get(x_field, ""))
        y = to_float(row.get(y_field, ""))
        if math.isfinite(x) and math.isfinite(y):
            points.append((x, y, row.get("mode", "unknown")))
    if not points:
        return

    x_values = np.asarray([point[0] for point in points])
    y_values = np.asarray([point[1] for point in points])
    sx = scale(x_values, left, left + plot_w)
    sy = scale(y_values, top, top + plot_h, invert=True)
    x_min, x_max = float(np.min(x_values)), float(np.max(x_values))
    y_min, y_max = float(np.min(y_values)), float(np.max(y_values))

    circles = []
    for (_, _, mode), cx, cy in zip(points, sx, sy):
        color = palette.get(mode, "#475569")
        circles.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="4.2" '
            f'fill="{color}" fill-opacity="0.72" />'
        )

    legend_items = []
    for index, mode in enumerate(sorted({point[2] for point in points})):
        color = palette.get(mode, "#475569")
        x0 = left + index * 76
        legend_items.append(
            f'<circle cx="{x0}" cy="{height - 28}" r="5" fill="{color}" />'
            f'<text x="{x0 + 12}" y="{height - 23}" class="legend">{mode}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .title {{ font: 700 20px system-ui, -apple-system, BlinkMacSystemFont, sans-serif; fill: #0f172a; }}
    .label {{ font: 13px system-ui, -apple-system, BlinkMacSystemFont, sans-serif; fill: #334155; }}
    .tick {{ font: 11px system-ui, -apple-system, BlinkMacSystemFont, sans-serif; fill: #64748b; }}
    .legend {{ font: 12px system-ui, -apple-system, BlinkMacSystemFont, sans-serif; fill: #334155; }}
    .axis {{ stroke: #334155; stroke-width: 1.2; }}
    .grid {{ stroke: #e2e8f0; stroke-width: 1; }}
  </style>
  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="{left}" y="32" class="title">{html.escape(title)}</text>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis" />
  <line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis" />
  <line x1="{left}" y1="{top}" x2="{left + plot_w}" y2="{top}" class="grid" />
  <line x1="{left}" y1="{top + plot_h / 2}" x2="{left + plot_w}" y2="{top + plot_h / 2}" class="grid" />
  <line x1="{left + plot_w}" y1="{top}" x2="{left + plot_w}" y2="{top + plot_h}" class="grid" />
  <text x="{left}" y="{top + plot_h + 35}" class="label">{html.escape(x_field)}</text>
  <text x="22" y="{top + plot_h / 2}" class="label" transform="rotate(-90 22 {top + plot_h / 2})">{html.escape(y_field)}</text>
  <text x="{left}" y="{top + plot_h + 18}" class="tick">{x_min:.4g}</text>
  <text x="{left + plot_w - 48}" y="{top + plot_h + 18}" class="tick">{x_max:.4g}</text>
  <text x="{left - 72}" y="{top + plot_h}" class="tick">{y_min:.4g}</text>
  <text x="{left - 72}" y="{top + 4}" class="tick">{y_max:.4g}</text>
  {"".join(circles)}
  {"".join(legend_items)}
</svg>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def parse_pair(raw: str) -> tuple[str, str, str]:
    parts = raw.split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(
            "Pairs must be x_field:y_field or x_field:y_field:title"
        )
    x_field, y_field = parts[:2]
    title = parts[2] if len(parts) == 3 else f"{x_field} vs {y_field}"
    return x_field, y_field, title


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "tables_dir",
        type=Path,
        help="Directory containing aggregated layer_metrics.csv and audio_features.csv.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--pair",
        action="append",
        type=parse_pair,
        help="Extra pair as x_field:y_field[:title]. Can be repeated.",
    )
    args = parser.parse_args()

    layer_rows = read_csv(args.tables_dir / "layer_metrics.csv")
    audio_rows = read_csv(args.tables_dir / "audio_features.csv")
    merged = join_layer_audio(layer_rows, audio_rows)
    if not merged:
        raise ValueError("No rows matched between layer_metrics.csv and audio_features.csv")

    pairs = DEFAULT_PAIRS + tuple(args.pair or ())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "analysis_dataset.csv", merged)
    write_csv(args.output_dir / "correlations.csv", correlation_rows(merged, pairs))

    for x_field, y_field, title in pairs:
        slug = f"{x_field}__vs__{y_field}".replace("/", "_")
        write_scatter_svg(
            args.output_dir / "scatter" / f"{slug}.svg",
            merged,
            x_field,
            y_field,
            title,
        )

    print(f"Wrote {len(merged)} joined rows to {args.output_dir / 'analysis_dataset.csv'}")
    print(f"Wrote correlations to {args.output_dir / 'correlations.csv'}")
    print(f"Wrote scatter plots to {args.output_dir / 'scatter'}")


if __name__ == "__main__":
    main()
