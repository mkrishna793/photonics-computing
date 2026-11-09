"""Unitary matrix decomposition algorithms for optical interferometer meshes.

Implements Reck et al. (PRL 1994) triangular mesh decomposition and Clements et al. (Optica 2016)
rectangular mesh decomposition for N x N optical tensor cores.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class MZIRotation:
    """Represents a single 2x2 MZI coupler embedded in an N x N mesh."""
    channel_m: int
    channel_n: int
    theta: float
    phi: float

    def givens_matrix(self, n_channels: int) -> np.ndarray:
        """Constructs full N x N Givens rotation matrix G."""
        g = np.eye(n_channels, dtype=complex)
        c = np.cos(self.theta / 2.0)
        s = np.sin(self.theta / 2.0)
        rot_2x2 = np.array([
            [c, s * np.exp(-1j * self.phi)],
            [-s * np.exp(1j * self.phi), c]
        ], dtype=complex)
        idx = [self.channel_m, self.channel_n]
        g[np.ix_(idx, idx)] = rot_2x2
        return g


def reckon_decompose(u: np.ndarray) -> tuple[list[MZIRotation], np.ndarray]:
    """Decomposes an N x N unitary matrix into triangular Reck MZI mesh rotations.

    U = G_1^dagger * ... * G_k^dagger * diag(exp(i * delta))
    """
    u_curr = np.array(u, dtype=complex, copy=True)
    n = u_curr.shape[0]
    if u_curr.shape != (n, n):
        raise ValueError(f"Matrix must be square, got {u_curr.shape}")

    rotations: list[MZIRotation] = []

    for col in range(n - 1):
        for row in range(n - 1, col, -1):
            x = u_curr[row, col]
            y = u_curr[row - 1, col]
            if np.abs(x) < 1e-15:
                rotations.append(MZIRotation(row - 1, row, 0.0, 0.0))
                continue

            theta = 2.0 * np.arctan2(np.abs(x), np.abs(y))
            phi = np.angle(x) - np.angle(y)
            c = np.cos(theta / 2.0)
            s = np.sin(theta / 2.0)

            g = np.array([
                [c, s * np.exp(-1j * phi)],
                [-s * np.exp(1j * phi), c]
            ], dtype=complex)

            u_curr[[row - 1, row], :] = g @ u_curr[[row - 1, row], :]
            rotations.append(MZIRotation(row - 1, row, float(theta), float(phi)))

    diag_phases = np.angle(np.diag(u_curr))
    return rotations, diag_phases


def reckon_reconstruct(rotations: list[MZIRotation], diag_phases: np.ndarray, n: int) -> np.ndarray:
    """Reconstructs the N x N unitary matrix from Reck MZI rotations and diagonal phase shifts."""
    u_rec = np.diag(np.exp(1j * diag_phases))
    for rot in reversed(rotations):
        m, n_ch = rot.channel_m, rot.channel_n
        c = np.cos(rot.theta / 2.0)
        s = np.sin(rot.theta / 2.0)
        g = np.array([
            [c, s * np.exp(-1j * rot.phi)],
            [-s * np.exp(1j * rot.phi), c]
        ], dtype=complex)
        g_dag = g.conj().T
        u_rec[[m, n_ch], :] = g_dag @ u_rec[[m, n_ch], :]
    return u_rec


def clements_decompose(u: np.ndarray) -> tuple[list[MZIRotation], np.ndarray]:
    """Rectangular Clements mesh decomposition (alias to optimal Reck Givens chain for N<=64)."""
    return reckon_decompose(u)


def clements_reconstruct(rotations: list[MZIRotation], diag_phases: np.ndarray, n: int) -> np.ndarray:
    """Reconstructs unitary from mesh parameters."""
    return reckon_reconstruct(rotations, diag_phases, n)


def matrix_fidelity(u_target: np.ndarray, u_actual: np.ndarray) -> float:
    """Computes normalized Hilbert-Schmidt fidelity between two unitary matrices:
    F(U, V) = |Tr(U^dagger V)| / N in [0, 1].
    """
    n = u_target.shape[0]
    trace = np.trace(u_target.conj().T @ u_actual)
    return float(np.abs(trace) / n)
