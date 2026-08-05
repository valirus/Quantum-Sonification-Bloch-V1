"""Extract analysis-ready STFT features from primary BFS/DFS layer WAV files."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import stft

PRIMARY_MODES = ("bfs", "dfs")
LAYER_PATTERN = re.compile(r"layer_(\d+)$")
SEED_PATTERN = re.compile(r"seed_(\d+)$")


def safe_weighted_mean(
    values: np.ndarray,
    weights: np.ndarray,
    axis: int = 0,
) -> np.ndarray:
    denominator = np.sum(weights, axis=axis)
    numerator = np.sum(values * weights, axis=axis)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )


def _zcr(signal: np.ndarray) -> float:
    if len(signal) <= 1:
        return 0.0
    return float(np.mean(np.abs(np.diff(np.signbit(signal)))))


def _find_seed(path: Path) -> int:
    for parent in path.parents:
        match = SEED_PATTERN.fullmatch(parent.name)
        if match:
            return int(match.group(1))
    raise ValueError(f"Could not infer seed from path: {path}")


def _infer_identity(path: Path) -> tuple[int, int, str]:
    mode = path.parent.name
    if mode not in PRIMARY_MODES:
        raise ValueError(f"Unsupported primary mode in path: {path}")

    match = LAYER_PATTERN.fullmatch(path.stem)
    if not match:
        raise ValueError(f"Could not infer layer from filename: {path.name}")

    return _find_seed(path), int(match.group(1)), mode


def _channel_power(
    signal: np.ndarray,
    sample_rate: int,
    nperseg: int,
    noverlap: int,
) -> tuple[np.ndarray, np.ndarray]:
    actual_nperseg = min(nperseg, max(8, len(signal)))
    actual_noverlap = min(
        noverlap,
        max(0, actual_nperseg - 1),
    )
    frequencies, _, spectrum = stft(
        signal,
        fs=sample_rate,
        window="hann",
        nperseg=actual_nperseg,
        noverlap=actual_noverlap,
        boundary=None,
        padded=False,
    )
    return frequencies, np.abs(spectrum) ** 2


def extract_features(
    path: Path,
    nperseg: int = 2048,
    noverlap: int = 1536,
) -> dict[str, float]:
    sample_rate, audio = wavfile.read(path)
    audio = np.asarray(audio, dtype=float)

    if audio.ndim == 1:
        left = right = audio
    elif audio.ndim == 2 and audio.shape[1] >= 2:
        left, right = audio[:, 0], audio[:, 1]
    else:
        raise ValueError(f"Unsupported WAV shape {audio.shape} for {path}")

    frequencies_left, power_left = _channel_power(
        left,
        sample_rate,
        nperseg,
        noverlap,
    )
    frequencies_right, power_right = _channel_power(
        right,
        sample_rate,
        nperseg,
        noverlap,
    )
    if not np.array_equal(frequencies_left, frequencies_right):
        raise ValueError("Left and right STFT frequency grids do not match.")

    frequencies = frequencies_left
    power = 0.5 * (power_left + power_right)
    frequency_grid = frequencies[:, None]

    centroid = safe_weighted_mean(frequency_grid, power, axis=0)
    bandwidth = np.sqrt(
        safe_weighted_mean(
            (frequency_grid - centroid[None, :]) ** 2,
            power,
            axis=0,
        )
    )

    power_sum = np.sum(power, axis=0, keepdims=True)
    normalized_power = np.divide(
        power,
        power_sum,
        out=np.zeros_like(power),
        where=power_sum > 0,
    )
    spectral_entropy = -np.sum(
        normalized_power * np.log2(normalized_power + 1e-15),
        axis=0,
    )
    spectral_flux = np.sqrt(
        np.sum(np.diff(normalized_power, axis=1) ** 2, axis=0)
    )

    rms_left = float(np.sqrt(np.mean(left**2)))
    rms_right = float(np.sqrt(np.mean(right**2)))
    rms_joint = float(
        np.sqrt(np.mean(0.5 * (left**2 + right**2)))
    )
    zcr_joint = 0.5 * (_zcr(left) + _zcr(right))
    stereo_balance = (
        (rms_right - rms_left) / (rms_right + rms_left + 1e-15)
    )
    stereo_correlation = (
        float(np.corrcoef(left, right)[0, 1])
        if np.std(left) > 0 and np.std(right) > 0
        else 0.0
    )
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0

    return {
        "sample_rate_hz": int(sample_rate),
        "duration_sec": float(len(left) / sample_rate),
        "peak_absolute_amplitude": peak,
        "rms_joint": rms_joint,
        "rms_left": rms_left,
        "rms_right": rms_right,
        "zero_crossing_rate_joint": float(zcr_joint),
        "spectral_centroid_mean_hz": float(np.mean(centroid)),
        "spectral_centroid_std_hz": float(np.std(centroid)),
        "spectral_bandwidth_mean_hz": float(np.mean(bandwidth)),
        "spectral_bandwidth_std_hz": float(np.std(bandwidth)),
        "spectral_entropy_mean": float(np.mean(spectral_entropy)),
        "spectral_entropy_std": float(np.std(spectral_entropy)),
        "spectral_flux_mean": (
            float(np.mean(spectral_flux)) if len(spectral_flux) else 0.0
        ),
        "stereo_balance": float(stereo_balance),
        "stereo_correlation": stereo_correlation,
        "stft_nperseg": int(min(nperseg, max(8, len(left)))),
        "stft_noverlap": int(
            min(noverlap, max(0, min(nperseg, max(8, len(left))) - 1))
        ),
    }


def _resolve_audio_root(path: Path) -> Path:
    if (path / "audio").is_dir():
        return path / "audio"
    return path


def collect_primary_files(audio_root: Path) -> list[Path]:
    files: list[Path] = []
    for mode in PRIMARY_MODES:
        mode_dir = audio_root / mode
        if mode_dir.is_dir():
            files.extend(sorted(mode_dir.glob("layer_*.wav")))
    return files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "audio_dir",
        type=Path,
        help="Either a seed run directory or its audio directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audio_features.csv"),
    )
    parser.add_argument("--nperseg", type=int, default=2048)
    parser.add_argument("--noverlap", type=int, default=1536)
    args = parser.parse_args()

    if args.nperseg < 8:
        raise ValueError("nperseg must be at least 8")
    if args.noverlap < 0:
        raise ValueError("noverlap must be non-negative")
    if args.noverlap >= args.nperseg:
        raise ValueError("noverlap must be smaller than nperseg")

    audio_root = _resolve_audio_root(args.audio_dir)
    files = collect_primary_files(audio_root)
    if not files:
        raise FileNotFoundError(
            f"No primary BFS/DFS layer WAV files found under {audio_root}"
        )

    rows = []
    for path in files:
        seed, layer, mode = _infer_identity(path)
        rows.append(
            {
                "seed": seed,
                "layer": layer,
                "mode": mode,
                "path": str(path),
                **extract_features(
                    path,
                    nperseg=args.nperseg,
                    noverlap=args.noverlap,
                ),
            }
        )

    rows.sort(key=lambda row: (row["seed"], row["layer"], row["mode"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} primary rows to {args.output}")


if __name__ == "__main__":
    main()
