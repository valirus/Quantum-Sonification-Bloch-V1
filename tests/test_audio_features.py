import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

from extract_stft_features import (
    _infer_identity,
    collect_primary_files,
    extract_features,
)


def test_primary_file_collection_excludes_combined_and_continuous(tmp_path):
    run_dir = tmp_path / "seed_000042"
    audio_dir = run_dir / "audio"
    for mode in ("bfs", "dfs", "combined"):
        (audio_dir / mode).mkdir(parents=True)
        (audio_dir / mode / "layer_00.wav").touch()
    (audio_dir / "bfs_continuous.wav").touch()

    files = collect_primary_files(audio_dir)
    assert {path.parent.name for path in files} == {"bfs", "dfs"}
    assert len(files) == 2


def test_identity_and_joint_stereo_features(tmp_path):
    path = (
        tmp_path
        / "seed_000007"
        / "audio"
        / "bfs"
        / "layer_03.wav"
    )
    path.parent.mkdir(parents=True)

    sample_rate = 8000
    time = np.arange(sample_rate, dtype=float) / sample_rate
    left = np.sin(2.0 * np.pi * 440.0 * time)
    right = 0.5 * np.sin(2.0 * np.pi * 440.0 * time)
    audio = np.column_stack([left, right]).astype(np.float32)
    wavfile.write(path, sample_rate, audio)

    assert _infer_identity(path) == (7, 3, "bfs")
    features = extract_features(path, nperseg=256, noverlap=128)
    assert features["sample_rate_hz"] == sample_rate
    assert features["peak_absolute_amplitude"] <= 1.0
    assert features["spectral_centroid_mean_hz"] > 0.0
    assert features["rms_left"] > features["rms_right"]
