"""Memristor Crossbar Array Engine with Differential Conductance and Parasitic IR Drops.

Implements analog in-memory computing acceleration for Lumiris Core Analog Algebra.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class MemristorConfig:
    """Device calibration parameters for analog memristive / ReRAM crossbars."""
    g_min: float = 1.0e-6        # Minimum conductance (1 uS)
    g_max: float = 100.0e-6      # Maximum conductance (100 uS)
    dac_levels: int = 64         # 6-bit programming resolution (64 levels)
    programming_noise_std: float = 0.01  # Relative programming noise (1%)
    drift_exponent: float = 0.05 # Empirical retention drift exponent nu: G(t) = G0 * (t/t0)^(-nu)
    t0_seconds: float = 1.0      # Reference time (1s)
    r_wire_ohm: float = 2.0      # Parasitic interconnect wire resistance per cell (2 Ohms)
    v_read_max: float = 0.2      # Read voltage amplitude (0.2 V, non-destructive read)
    transimpedance_rf_ohm: float = 1.0e5 # TIA feedback resistance (100 kOhm)


class MemristorCrossbar:
    """M x N Differential Memristor Crossbar Array.

    Implements matrix-vector multiplication Y = W @ X via Kirchhoff's Current Law:
        W_ij = alpha * (G_ij^+ - G_ij^-)
        I_j = sum_i V_i * G_ij
        V_out_j = R_f * (I_j^+ - I_j^-)
    """

    def __init__(
        self,
        n_rows: int,
        n_cols: int,
        config: Optional[MemristorConfig] = None,
    ) -> None:
        self.n_rows = int(n_rows)
        self.n_cols = int(n_cols)
        self.cfg = config or MemristorConfig()

        # Conductance arrays for differential pairs
        self.g_pos = np.full((self.n_rows, self.n_cols), self.cfg.g_min, dtype=float)
        self.g_neg = np.full((self.n_rows, self.n_cols), self.cfg.g_min, dtype=float)
        self.scale_alpha: float = 1.0
        self.target_weight_matrix: np.ndarray = np.zeros((self.n_rows, self.n_cols))

    def quantize_conductance(self, g: np.ndarray) -> np.ndarray:
        """Quantizes conductance values to discrete DAC programming levels."""
        g_clipped = np.clip(g, self.cfg.g_min, self.cfg.g_max)
        step = (self.cfg.g_max - self.cfg.g_min) / (self.cfg.dac_levels - 1)
        levels = np.round((g_clipped - self.cfg.g_min) / step)
        return self.cfg.g_min + levels * step

    def program_weights(self, weights: np.ndarray, noisy: bool = True) -> float:
        """Programs target weight matrix W into differential conductance pairs.

        Returns the maximum conductance mapping error.
        """
        w = np.asarray(weights, dtype=float)
        if w.shape != (self.n_rows, self.n_cols):
            raise ValueError(f"Weight shape {w.shape} != crossbar shape ({self.n_rows}, {self.n_cols})")

        self.target_weight_matrix = np.array(w, copy=True)
        w_max = float(np.max(np.abs(w)))
        if w_max < 1e-12:
            w_max = 1.0

        # Scale factor alpha maps [-W_max, W_max] -> [G_min, G_max]
        dynamic_range = self.cfg.g_max - self.cfg.g_min
        self.scale_alpha = dynamic_range / (2.0 * w_max)

        g_p = np.zeros_like(w)
        g_n = np.zeros_like(w)

        for i in range(self.n_rows):
            for j in range(self.n_cols):
                val = w[i, j]
                if val >= 0.0:
                    g_p[i, j] = self.cfg.g_min + val * self.scale_alpha * 2.0
                    g_n[i, j] = self.cfg.g_min
                else:
                    g_p[i, j] = self.cfg.g_min
                    g_n[i, j] = self.cfg.g_min - val * self.scale_alpha * 2.0

        # Apply DAC quantization
        g_p_quant = self.quantize_conductance(g_p)
        g_n_quant = self.quantize_conductance(g_n)

        # Apply programming noise if enabled
        if noisy and self.cfg.programming_noise_std > 0.0:
            noise_p = np.random.normal(0.0, self.cfg.programming_noise_std * self.cfg.g_max, g_p.shape)
            noise_n = np.random.normal(0.0, self.cfg.programming_noise_std * self.cfg.g_max, g_n.shape)
            g_p_quant = np.clip(g_p_quant + noise_p, self.cfg.g_min, self.cfg.g_max)
            g_n_quant = np.clip(g_n_quant + noise_n, self.cfg.g_min, self.cfg.g_max)

        self.g_pos = g_p_quant
        self.g_neg = g_n_quant

        # Calculate actual programmed weights
        w_programmed = (self.g_pos - self.g_neg) / (2.0 * self.scale_alpha)
        max_error = float(np.max(np.abs(w - w_programmed)))
        return max_error

    def apply_drift(self, elapsed_seconds: float) -> None:
        """Simulates conductance drift over time: G(t) = G0 * (t / t0)^(-nu)."""
        if elapsed_seconds <= self.cfg.t0_seconds:
            return
        decay_factor = (elapsed_seconds / self.cfg.t0_seconds) ** (-self.cfg.drift_exponent)
        self.g_pos = np.clip(self.g_pos * decay_factor, self.cfg.g_min, self.cfg.g_max)
        self.g_neg = np.clip(self.g_neg * decay_factor, self.cfg.g_min, self.cfg.g_max)

    def forward(
        self,
        v_in: np.ndarray,
        include_ir_drop: bool = True,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """Executes analog vector-matrix multiplication.

        Inputs:
            v_in: Input voltage vector of length n_rows.
            include_ir_drop: Whether to simulate parasitic wire resistance attenuation.

        Returns:
            v_out: Output voltage vector of length n_cols.
            metrics: Computational and physical metrics (power, IR drop error).
        """
        v = np.asarray(v_in, dtype=float)
        if v.shape != (self.n_rows,):
            raise ValueError(f"Input shape {v.shape} != ({self.n_rows},)")

        # Scale input voltage to read range
        v_norm = np.clip(v, -self.cfg.v_read_max, self.cfg.v_read_max)

        if not include_ir_drop or self.cfg.r_wire_ohm <= 0.0:
            # Ideal KCL
            i_pos = self.g_pos.T @ np.maximum(v_norm, 0.0) + self.g_neg.T @ np.maximum(-v_norm, 0.0)
            i_neg = self.g_neg.T @ np.maximum(v_norm, 0.0) + self.g_pos.T @ np.maximum(-v_norm, 0.0)
        else:
            # Parasitic wire IR drop approximation:
            # Voltage attenuates along row wires and column wires
            i_pos = np.zeros(self.n_cols)
            i_neg = np.zeros(self.n_cols)
            g_avg = 0.5 * (self.cfg.g_max + self.cfg.g_min)
            for col in range(self.n_cols):
                for row in range(self.n_rows):
                    # Wire resistance attenuation along Manhattan distance (row + col)
                    attenuation = np.exp(-float(row + col) * self.cfg.r_wire_ohm * g_avg)
                    v_cell = v_norm[row] * attenuation
                    if v_cell >= 0:
                        i_pos[col] += v_cell * self.g_pos[row, col]
                        i_neg[col] += v_cell * self.g_neg[row, col]
                    else:
                        i_pos[col] += (-v_cell) * self.g_neg[row, col]
                        i_neg[col] += (-v_cell) * self.g_pos[row, col]

        # Differential TIA output
        i_diff = i_pos - i_neg
        v_out = self.cfg.transimpedance_rf_ohm * i_diff

        # Map back to mathematical weight space: Y = W @ X
        # I_diff = sum_i V_i * (G^+ - G^-) = 2 * alpha * sum_i V_i * W_ij
        y_recon = i_diff / (2.0 * self.scale_alpha)

        # Power dissipation P = sum(V * I)
        total_current = np.sum(i_pos + i_neg)
        power_watts = float(np.mean(np.abs(v_norm)) * total_current)

        metrics = {
            "total_current_amperes": float(total_current),
            "power_watts": power_watts,
            "scale_alpha": self.scale_alpha,
        }
        return y_recon, metrics
