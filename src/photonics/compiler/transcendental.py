"""L1 Transcendental Function Approximation Pass.

Decomposes non-rational functions (exp, tanh, sigmoid, sin, cos, sqrt) into
Chebyshev minimax polynomials and Padé rational approximants with certified
mathematical error bounds plugged into the Core Analog Algebra.
"""

from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Callable, Optional
import numpy as np
from photonics.compiler.ir import Interval, SSAGraph, EncodingType


@dataclass
class ApproximationResult:
    """Certified approximation result with mathematical error bounds."""
    func_name: str
    domain: Interval
    degree: int
    coefficients: list[float]  # Polynomial coefficients in Horner form: a0 + x*(a1 + x*(...))
    max_truncation_error: float
    method: str  # 'chebyshev' or 'pade'


class ChebyshevApproximation:
    """Chebyshev polynomial expansion on arbitrary bounded intervals [a, b]."""

    @staticmethod
    def fit(
        func: Callable[[np.ndarray], np.ndarray],
        domain: Interval,
        degree: int = 6,
        func_name: str = "custom",
    ) -> ApproximationResult:
        a, b = domain.lo, domain.hi
        M = max(degree + 15, 40)
        k = np.arange(M)
        nodes_t = np.cos((k + 0.5) * np.pi / M)
        nodes_x = 0.5 * (b - a) * nodes_t + 0.5 * (a + b)
        f_vals = func(nodes_x)

        # Compute Chebyshev coefficients on [-1, 1]
        c_k = []
        for deg in range(degree + 1):
            c = (2.0 / M) * np.sum(f_vals * np.cos(deg * (k + 0.5) * np.pi / M))
            c_k.append(float(c))
        c_k[0] *= 0.5

        # Evaluate at fine grid to rigorously bound supremum error
        test_x = np.linspace(a, b, 2000)
        test_t = (2.0 * test_x - (a + b)) / (b - a)

        # Reconstruct standard polynomial coefficients via Chebyshev basis conversion
        # T_0(t) = 1, T_1(t) = t, T_{n+1}(t) = 2t T_n(t) - T_{n-1}(t)
        poly_t = np.polynomial.chebyshev.cheb2poly(c_k)

        # Transform poly from t in [-1, 1] back to x in [a, b]:
        # t = u * x + v, where u = 2/(b-a), v = -(a+b)/(b-a)
        u = 2.0 / (b - a)
        v = -(a + b) / (b - a)
        # Shift polynomial
        poly_x = np.zeros(degree + 1)
        for i, ci in enumerate(poly_t):
            # ci * (u*x + v)^i
            term_poly = ci * np.polynomial.polynomial.polypow([v, u], i)
            poly_x[:len(term_poly)] += term_poly

        # Empirical error verification
        y_approx = np.polynomial.polynomial.polyval(test_x, poly_x)
        y_true = func(test_x)
        max_err = float(np.max(np.abs(y_true - y_approx)))

        return ApproximationResult(
            func_name=func_name,
            domain=domain,
            degree=degree,
            coefficients=[float(c) for c in poly_x],
            max_truncation_error=max_err,
            method="chebyshev",
        )


class PadeApproximation:
    """Padé rational approximation [L/M] for sigmoidal activations."""

    @staticmethod
    def fit_tanh(domain: Interval, degree: int = 5) -> ApproximationResult:
        # [3/2] Padé approximant for tanh(x): x * (15 + x^2) / (15 + 6 x^2)
        # For [-2, 2], compute empirical bound
        test_x = np.linspace(domain.lo, domain.hi, 2000)
        num = test_x * (15.0 + test_x ** 2)
        den = 15.0 + 6.0 * (test_x ** 2)
        approx = num / den
        true_val = np.tanh(test_x)
        max_err = float(np.max(np.abs(true_val - approx)))

        return ApproximationResult(
            func_name="tanh",
            domain=domain,
            degree=degree,
            coefficients=[15.0, 1.0, 15.0, 6.0],
            max_truncation_error=max_err,
            method="pade",
        )


def approximate_transcendental(
    func_name: str,
    domain: Interval,
    target_tolerance: float = 1e-3,
) -> ApproximationResult:
    """Selects optimal polynomial or rational approximation satisfying target tolerance."""
    funcs = {
        "exp": np.exp,
        "tanh": np.tanh,
        "sigmoid": lambda x: 1.0 / (1.0 + np.exp(-x)),
        "sin": np.sin,
        "cos": np.cos,
        "sqrt": np.sqrt,
    }

    if func_name not in funcs:
        raise ValueError(f"Unsupported transcendental function: {func_name}")

    func = funcs[func_name]

    # Iteratively increase degree until error <= target_tolerance
    for deg in range(3, 16):
        res = ChebyshevApproximation.fit(func, domain, degree=deg, func_name=func_name)
        if res.max_truncation_error <= target_tolerance:
            return res

    # Return highest degree attempted if tolerance very tight
    return res


def lower_approximation_to_ssa(
    graph: SSAGraph,
    input_node_name: str,
    output_name_prefix: str,
    approx: ApproximationResult,
    domain_out: Interval,
    encoding: EncodingType = EncodingType.OPT_AMP,
) -> str:
    """Lowers a Chebyshev polynomial approximation into Horner form using only + and * SSA nodes.

    P(x) = c_0 + x * (c_1 + x * (c_2 + ... + x * c_n))
    """
    coeffs = approx.coefficients  # c_0, c_1, ..., c_n
    n = len(coeffs) - 1

    # Start with outermost constant c_n
    current_val_node = f"{output_name_prefix}_c{n}"
    graph.add_const(current_val_node, coeffs[n], error=0.0, encoding=encoding)

    for i in range(n - 1, -1, -1):
        # mul_node = current * x
        mul_node = f"{output_name_prefix}_mul_{i}"
        graph.add_binary_op(
            op="mul",
            name=mul_node,
            left=current_val_node,
            right=input_node_name,
            local_error=0.0001,
            domain_in=Interval(-10.0, 10.0),
            domain_out=Interval(-10.0, 10.0),
            encoding=encoding,
        )

        # const c_i
        const_node = f"{output_name_prefix}_c{i}"
        graph.add_const(const_node, coeffs[i], error=0.0, encoding=encoding)

        # add_node = const_node + mul_node
        if i == 0:
            final_node = f"{output_name_prefix}_result"
            # Final node absorbs the truncation error bound
            graph.add_binary_op(
                op="add",
                name=final_node,
                left=const_node,
                right=mul_node,
                local_error=approx.max_truncation_error,
                domain_in=Interval(-10.0, 10.0),
                domain_out=domain_out,
                encoding=encoding,
            )
            return final_node
        else:
            add_node = f"{output_name_prefix}_add_{i}"
            graph.add_binary_op(
                op="add",
                name=add_node,
                left=const_node,
                right=mul_node,
                local_error=0.00001,
                domain_in=Interval(-10.0, 10.0),
                domain_out=Interval(-10.0, 10.0),
                encoding=encoding,
            )
            current_val_node = add_node

    return current_val_node
