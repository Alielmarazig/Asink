"""
Core synchronization engine.

Uses FFT-based cross-correlation of audio waveforms to find
time offsets between multiple clips. Same fundamental approach
as PluralEyes: extract audio, downsample, cross-correlate,
find peak offset.
"""

import numpy as np
from scipy import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

SYNC_SAMPLE_RATE = 8000  # Downsample to 8kHz for faster correlation
CHUNK_DURATION = 300     # Process up to 5 minutes at a time


@dataclass
class SyncResult:
    """Result of syncing one clip against the reference."""
    clip_path: Path
    offset_samples: int
    offset_seconds: float
    confidence: float  # 0-1, based on correlation peak strength
    sample_rate: int
    success: bool
    error: Optional[str] = None


@dataclass
class SyncSession:
    """A complete sync session with multiple clips."""
    reference_path: Optional[Path] = None
    clip_paths: list[Path] = field(default_factory=list)
    results: list[SyncResult] = field(default_factory=list)
    sample_rate: int = SYNC_SAMPLE_RATE


class SyncEngine:
    """
    Audio cross-correlation sync engine.

    Algorithm:
    1. Extract mono audio from each clip via FFmpeg
    2. Downsample all to a common low rate (8kHz) for speed
    3. Pick the first clip as reference (or let user choose)
    4. Cross-correlate each clip against reference
    5. Peak of correlation = time offset
    6. Confidence = peak height relative to signal energy
    """

    def __init__(self, sample_rate: int = SYNC_SAMPLE_RATE):
        self.sample_rate = sample_rate

    def extract_audio(self, filepath: Path) -> np.ndarray:
        """
        Extract mono audio from any media file using FFmpeg.
        Returns numpy array at self.sample_rate.
        """
        import subprocess
        import tempfile
        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = [
            "ffmpeg", "-y",
            "-i", str(filepath),
            "-ac", "1",                          # mono
            "-ar", str(self.sample_rate),         # target sample rate
            "-sample_fmt", "s16",                 # 16-bit PCM
            "-vn",                                # no video
            "-loglevel", "error",
            tmp_path
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            audio, sr = sf.read(tmp_path, dtype="float32")
            return audio
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg failed on {filepath.name}: {e.stderr.decode()}"
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def cross_correlate(
        self,
        reference: np.ndarray,
        target: np.ndarray
    ) -> tuple[int, float]:
        """
        FFT-based cross-correlation between two audio signals.

        Returns:
            offset_samples: positive = target starts after reference
            confidence: normalized correlation peak (0-1)
        """
        # Normalize both signals
        ref_norm = reference - np.mean(reference)
        tgt_norm = target - np.mean(target)

        ref_energy = np.sqrt(np.sum(ref_norm ** 2))
        tgt_energy = np.sqrt(np.sum(tgt_norm ** 2))

        if ref_energy < 1e-10 or tgt_energy < 1e-10:
            logger.warning("One of the signals is silent or near-silent.")
            return 0, 0.0

        # FFT cross-correlation (much faster than direct for long signals)
        correlation = signal.fftconvolve(ref_norm, tgt_norm[::-1], mode="full")

        # Find the peak
        peak_index = np.argmax(np.abs(correlation))
        peak_value = np.abs(correlation[peak_index])

        # Offset: positive means target is delayed relative to reference
        offset = peak_index - (len(target) - 1)

        # Confidence: normalized correlation coefficient at peak
        confidence = peak_value / (ref_energy * tgt_energy)
        confidence = min(confidence, 1.0)

        return int(offset), float(confidence)

    def sync_clips(
        self,
        clip_paths: list[Path],
        reference_index: int = 0,
        progress_callback=None
    ) -> SyncSession:
        """
        Sync multiple clips against a reference clip.

        Args:
            clip_paths: list of media file paths
            reference_index: which clip to use as reference (0-based)
            progress_callback: optional fn(current, total, message)

        Returns:
            SyncSession with all results
        """
        session = SyncSession(
            reference_path=clip_paths[reference_index],
            clip_paths=list(clip_paths),
        )

        total = len(clip_paths)

        if progress_callback:
            progress_callback(0, total, "Extracting reference audio...")

        # Extract reference audio
        try:
            ref_audio = self.extract_audio(clip_paths[reference_index])
        except Exception as e:
            logger.error(f"Failed to extract reference audio: {e}")
            for path in clip_paths:
                session.results.append(SyncResult(
                    clip_path=path,
                    offset_samples=0,
                    offset_seconds=0.0,
                    confidence=0.0,
                    sample_rate=self.sample_rate,
                    success=False,
                    error=f"Reference extraction failed: {e}"
                ))
            return session

        # Sync each clip
        for i, clip_path in enumerate(clip_paths):
            if progress_callback:
                progress_callback(
                    i + 1, total,
                    f"Syncing {clip_path.name}..."
                )

            if i == reference_index:
                # Reference clip has zero offset by definition
                session.results.append(SyncResult(
                    clip_path=clip_path,
                    offset_samples=0,
                    offset_seconds=0.0,
                    confidence=1.0,
                    sample_rate=self.sample_rate,
                    success=True,
                ))
                continue

            try:
                target_audio = self.extract_audio(clip_path)
                offset_samples, confidence = self.cross_correlate(
                    ref_audio, target_audio
                )
                offset_seconds = offset_samples / self.sample_rate

                session.results.append(SyncResult(
                    clip_path=clip_path,
                    offset_samples=offset_samples,
                    offset_seconds=offset_seconds,
                    confidence=confidence,
                    sample_rate=self.sample_rate,
                    success=confidence > 0.05,  # threshold for "good sync"
                ))

                if confidence < 0.05:
                    logger.warning(
                        f"Low confidence sync for {clip_path.name}: "
                        f"{confidence:.3f}"
                    )

            except Exception as e:
                logger.error(f"Sync failed for {clip_path.name}: {e}")
                session.results.append(SyncResult(
                    clip_path=clip_path,
                    offset_samples=0,
                    offset_seconds=0.0,
                    confidence=0.0,
                    sample_rate=self.sample_rate,
                    success=False,
                    error=str(e),
                ))

        if progress_callback:
            progress_callback(total, total, "Sync complete.")

        return session
