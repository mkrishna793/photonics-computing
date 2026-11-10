"""Hardware Lowering Engine: Maps SSA Core Analog Algebra to Optical Meshes & Memristor Crossbars."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
import numpy as np
from photonics.compiler.ir import SSAGraph, SSANode
from photonics.devices.memristor import MemristorCrossbar, MemristorConfig
from photonics.simulation.optical_engine import OpticalTensorCore


@dataclass
class HardwareDeviceConfig:
    """Device specification for hardware lowering."""
    backend_type: str = "optical_mesh"  # 'optical_mesh' or 'memristor_crossbar'
    dac_bits: int = 12
    voltage_max: float = 5.0
    phase_per_v2: float = 0.392699       # rad / V^2
    phase_offset: float = 0.0
    phase_residual_error: float = 1.0e-5 # Bounded calibration error
    waveguide_input_limit: float = 1.0


@dataclass
class CompiledHardwareBundle:
    """Emitted physical control artifact ready for chip programming and certificate auditing."""
    program_name: str
    backend_type: str
    target_shape: tuple[int, int]
    control_registers: dict[str, Any]
    physical_error_bound: float
    arithmetic_error_bound: float
    status: str = "COMPILED"
    metadata: dict[str, Any] = field(default_factory=dict)


class OpticalMeshBackend:
    """Compiles linear algebra and GEMM SSA nodes to programmable MZI meshes."""

    def __init__(self, config: Optional[HardwareDeviceConfig] = None) -> None:
        self.cfg = config or HardwareDeviceConfig()

    def lower_gemm(
        self,
        weight_matrix: np.ndarray,
        node_name: str = "gemm_node",
    ) -> CompiledHardwareBundle:
        """Lowers an N x N or M x N weight matrix to MZI phase angles, DAC codes, and heater voltages."""
        w = np.asarray(weight_matrix, dtype=complex)
        n_rows, n_cols = w.shape
        n_dim = max(n_rows, n_cols)

        # Pad to square if needed
        if n_rows != n_cols:
            w_sq = np.eye(n_dim, dtype=complex)
            w_sq[:n_rows, :n_cols] = w
        else:
            w_sq = w

        core = OpticalTensorCore(n_channels=n_dim, enable_thermal_crosstalk=True, precompensate_crosstalk=True)
        core.set_general_matrix(w_sq)

        # Lower U and V^dagger rotations to DAC codes and voltages
        dac_levels = 2 ** self.cfg.dac_bits
        v_max = self.cfg.voltage_max

        all_rotations = core.u_rotations + core.vh_rotations
        phase_records = []
        max_dac_quant_err = 0.0

        for idx, rot in enumerate(all_rotations):
            # Target phase theta in [0, 2*pi]
            th = float(rot.theta % (2.0 * np.pi))

            # Invert thermo-optic response: theta = phase_offset + phase_per_v2 * V^2
            # V = sqrt((theta - phase_offset) / phase_per_v2)
            v_req = np.sqrt(max(0.0, th - self.cfg.phase_offset) / self.cfg.phase_per_v2)
            v_clamped = min(v_req, v_max)

            # DAC quantization
            dac_code = int(np.round((v_clamped / v_max) * (dac_levels - 1)))
            v_actual = (dac_code / (dac_levels - 1)) * v_max
            th_actual = self.cfg.phase_offset + self.cfg.phase_per_v2 * (v_actual ** 2)

            quant_err = abs(th - th_actual)
            max_dac_quant_err = max(max_dac_quant_err, quant_err)

            phase_records.append({
                "mzi_id": idx,
                "channel_m": rot.channel_m,
                "channel_n": rot.channel_n,
                "target_theta_rad": th,
                "target_phi_rad": float(rot.phi),
                "heater_voltage_v": float(v_actual),
                "dac_code": dac_code,
                "dac_levels": dac_levels,
            })

        # Physical error bound = DAC quantization + bounded calibration error
        total_phys_error = max_dac_quant_err + self.cfg.phase_residual_error

        control_regs = {
            "mzi_stages": phase_records,
            "singular_values": [float(s) for s in core.singular_values],
            "u_diag_phases": [float(p) for p in core.u_diag],
            "vh_diag_phases": [float(p) for p in core.vh_diag],
            "total_mzis": len(all_rotations),
        }

        return CompiledHardwareBundle(
            program_name=node_name,
            backend_type="optical_mesh",
            target_shape=(n_rows, n_cols),
            control_registers=control_regs,
            physical_error_bound=total_phys_error,
            arithmetic_error_bound=total_phys_error * n_dim,
            metadata={"mzi_count": len(all_rotations), "dimension": n_dim},
        )


class MemristorCrossbarBackend:
    """Compiles linear algebra and GEMM SSA nodes to differential memristor crossbars."""

    def __init__(self, memristor_config: Optional[MemristorConfig] = None) -> None:
        self.mem_cfg = memristor_config or MemristorConfig()

    def lower_gemm(
        self,
        weight_matrix: np.ndarray,
        node_name: str = "gemm_node",
    ) -> CompiledHardwareBundle:
        """Lowers an M x N weight matrix to differential conductance pairs and read voltages."""
        w = np.asarray(weight_matrix, dtype=float)
        n_rows, n_cols = w.shape

        crossbar = MemristorCrossbar(n_rows=n_rows, n_cols=n_cols, config=self.mem_cfg)
        prog_error = crossbar.program_weights(w, noisy=False)

        # Control registers: G_pos and G_neg arrays and scaling alpha
        control_regs = {
            "g_pos_siemens": crossbar.g_pos.tolist(),
            "g_neg_siemens": crossbar.g_neg.tolist(),
            "scale_alpha": crossbar.scale_alpha,
            "v_read_max_volts": self.mem_cfg.v_read_max,
            "transimpedance_rf_ohms": self.mem_cfg.transimpedance_rf_ohm,
            "dac_levels": self.mem_cfg.dac_levels,
        }

        # Composed physical error bound including programming quantization
        phys_error = prog_error + (self.mem_cfg.programming_noise_std * np.max(np.abs(w)))

        return CompiledHardwareBundle(
            program_name=node_name,
            backend_type="memristor_crossbar",
            target_shape=(n_rows, n_cols),
            control_registers=control_regs,
            physical_error_bound=float(phys_error),
            arithmetic_error_bound=float(phys_error * n_cols),
            metadata={"rows": n_rows, "cols": n_cols, "total_cells": 2 * n_rows * n_cols},
        )
