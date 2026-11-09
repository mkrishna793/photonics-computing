"""Tests for unitary decomposition and mesh reconstruction."""

import numpy as np
import pytest
from scipy.stats import unitary_group
from photonics.core.unitary import (
    reckon_decompose,
    reckon_reconstruct,
    matrix_fidelity,
)


@pytest.mark.parametrize("n", [2, 3, 4, 6])
def test_reck_decomposition_reconstruction(n):
    np.random.seed(42 + n)
    u_target = unitary_group.rvs(n)
    rotations, diag_phases = reckon_decompose(u_target)

    # Check number of rotations equals N(N-1)/2
    assert len(rotations) == (n * (n - 1)) // 2

    u_rec = reckon_reconstruct(rotations, diag_phases, n)
    frobenius_error = np.linalg.norm(u_target - u_rec)
    assert frobenius_error < 1e-12

    fid = matrix_fidelity(u_target, u_rec)
    assert pytest.approx(fid, abs=1e-10) == 1.0
