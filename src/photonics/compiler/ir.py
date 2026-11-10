"""SSA Intermediate Representation with Physical Encodings and Bounded Error Contracts.

Implements the L2 Core Analog Algebra for Lumiris with tight interval arithmetic,
domain containment validation, and fail-closed error propagation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import math
from typing import Any, Optional


class EncodingType(str, Enum):
    """Physical encoding dimensions for analog and optical quantities."""
    OPT_AMP = "OptAmp"    # Coherent optical field amplitude E (complex, |E| <= E_max)
    OPT_POW = "OptPow"    # Optical power P = |E|^2 (nonnegative, [0, P_max])
    VOLT = "Volt"          # Electrical potential [V_min, V_max] (V)
    CURR = "Curr"          # Electrical current [I_min, I_max] (A)
    COND = "Cond"          # Memristor conductance [G_min, G_max] > 0 (Siemens)
    DIGITAL = "Digital"    # Digital discrete representation (bits/integers)


@dataclass(frozen=True)
class Interval:
    """Exact bounded real interval [lo, hi]."""
    lo: float
    hi: float

    def __post_init__(self):
        if self.lo > self.hi:
            raise ValueError(f"Invalid interval: lo ({self.lo}) > hi ({self.hi})")

    @classmethod
    def point(cls, val: float) -> Interval:
        return cls(float(val), float(val))

    @property
    def magnitude(self) -> float:
        """Maximum absolute value: max(|lo|, |hi|)."""
        return max(abs(self.lo), abs(self.hi))

    @property
    def min_magnitude(self) -> float:
        """Minimum absolute value over the interval."""
        if self.lo <= 0.0 <= self.hi:
            return 0.0
        return min(abs(self.lo), abs(self.hi))

    def contains(self, other: Interval) -> bool:
        """True if other is completely contained within self."""
        return self.lo <= other.lo and other.hi <= self.hi

    def expand(self, error: float) -> Interval:
        """Expands interval by +/- error."""
        if error < 0.0:
            raise ValueError(f"Error must be nonnegative, got {error}")
        return Interval(self.lo - error, self.hi + error)

    def add(self, other: Interval) -> Interval:
        return Interval(self.lo + other.lo, self.hi + other.hi)

    def sub(self, other: Interval) -> Interval:
        return Interval(self.lo - other.hi, self.hi - other.lo)

    def mul(self, other: Interval) -> Interval:
        """Sign-preserving interval multiplication using all four endpoint products."""
        p = [
            self.lo * other.lo,
            self.lo * other.hi,
            self.hi * other.lo,
            self.hi * other.hi,
        ]
        return Interval(min(p), max(p))

    def div(self, other: Interval) -> Interval:
        """Interval division. Fails closed if denominator touches or crosses zero."""
        if other.lo <= 0.0 <= other.hi:
            raise ValueError(f"Unsafe interval division: denominator {other} contains zero")
        recip_lo = 1.0 / other.hi
        recip_hi = 1.0 / other.lo
        recip = Interval(recip_lo, recip_hi)
        return self.mul(recip)


@dataclass
class SSANode:
    """Single-Static Assignment node in the Core Analog Algebra graph."""
    name: str
    op: str  # 'input', 'const', 'add', 'sub', 'mul', 'div', 'gemm', 'transcendental'
    operands: list[str] = field(default_factory=list)
    encoding: EncodingType = EncodingType.OPT_AMP
    ideal_interval: Interval = field(default_factory=lambda: Interval(0.0, 0.0))
    local_error: float = 0.0
    composed_error: float = 0.0
    domain_in: Interval = field(default_factory=lambda: Interval(-1.0, 1.0))
    domain_out: Interval = field(default_factory=lambda: Interval(-1.0, 1.0))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expanded_interval(self) -> Interval:
        return self.ideal_interval.expand(self.composed_error)


class SSAGraph:
    """Directed Acyclic Graph of SSA operations representing the computation."""

    def __init__(self, name: str = "lumiris_program") -> None:
        self.name = name
        self.nodes: dict[str, SSANode] = {}
        self.topological_order: list[str] = []
        self.output_node: Optional[str] = None
        self.requested_tolerance: float = 0.0

    def add_input(
        self,
        name: str,
        lo: float,
        hi: float,
        error: float,
        encoding: EncodingType = EncodingType.OPT_AMP,
    ) -> SSANode:
        if name in self.nodes:
            raise ValueError(f"Duplicate node name: {name}")
        interval = Interval(lo, hi)
        node = SSANode(
            name=name,
            op="input",
            encoding=encoding,
            ideal_interval=interval,
            local_error=error,
            composed_error=error,
            domain_in=interval.expand(error),
            domain_out=interval.expand(error),
        )
        self.nodes[name] = node
        self.topological_order.append(name)
        return node

    def add_const(
        self,
        name: str,
        value: float,
        error: float = 0.0,
        encoding: EncodingType = EncodingType.OPT_AMP,
    ) -> SSANode:
        if name in self.nodes:
            raise ValueError(f"Duplicate node name: {name}")
        interval = Interval.point(value)
        node = SSANode(
            name=name,
            op="const",
            encoding=encoding,
            ideal_interval=interval,
            local_error=error,
            composed_error=error,
            domain_in=interval.expand(error),
            domain_out=interval.expand(error),
        )
        self.nodes[name] = node
        self.topological_order.append(name)
        return node

    def add_binary_op(
        self,
        op: str,
        name: str,
        left: str,
        right: str,
        local_error: float,
        domain_in: Interval,
        domain_out: Interval,
        encoding: Optional[EncodingType] = None,
    ) -> SSANode:
        if name in self.nodes:
            raise ValueError(f"Duplicate node name: {name}")
        if left not in self.nodes or right not in self.nodes:
            raise ValueError(f"Operands {left}, {right} must precede node {name}")

        enc = encoding or self.nodes[left].encoding
        node = SSANode(
            name=name,
            op=op,
            operands=[left, right],
            encoding=enc,
            local_error=float(local_error),
            domain_in=domain_in,
            domain_out=domain_out,
        )
        self.nodes[name] = node
        self.topological_order.append(name)
        return node

    def add_gemm(
        self,
        name: str,
        weight_matrix_name: str,
        vector_in_name: str,
        matrix_shape: tuple[int, int],
        local_error: float,
        domain_in: Interval,
        domain_out: Interval,
        encoding: EncodingType = EncodingType.OPT_AMP,
    ) -> SSANode:
        """Matrix-vector multiplication node (N x N or M x N)."""
        if name in self.nodes:
            raise ValueError(f"Duplicate node name: {name}")
        node = SSANode(
            name=name,
            op="gemm",
            operands=[weight_matrix_name, vector_in_name],
            encoding=encoding,
            local_error=float(local_error),
            domain_in=domain_in,
            domain_out=domain_out,
            metadata={"shape": matrix_shape},
        )
        self.nodes[name] = node
        self.topological_order.append(name)
        return node

    def add_transcendental(
        self,
        name: str,
        input_name: str,
        func_name: str,
        approx_error: float,
        domain_in: Interval,
        domain_out: Interval,
        degree: int,
        encoding: EncodingType = EncodingType.OPT_AMP,
    ) -> SSANode:
        """L1 approximation node (exp, tanh, sigmoid, sin, cos, sqrt)."""
        if name in self.nodes:
            raise ValueError(f"Duplicate node name: {name}")
        node = SSANode(
            name=name,
            op="transcendental",
            operands=[input_name],
            encoding=encoding,
            local_error=float(approx_error),
            domain_in=domain_in,
            domain_out=domain_out,
            metadata={"func": func_name, "degree": degree},
        )
        self.nodes[name] = node
        self.topological_order.append(name)
        return node

    def set_output(self, name: str, tolerance: float) -> None:
        if name not in self.nodes:
            raise ValueError(f"Output node {name} does not exist")
        self.output_node = name
        self.requested_tolerance = float(tolerance)


def verify_graph_contracts(graph: SSAGraph) -> dict[str, Any]:
    """Evaluates interval semantics, checks input/output physical domains, and computes error bounds.

    Fails closed on any contract violation, saturation, or unsafe divisor.
    """
    for node_name in graph.topological_order:
        node = graph.nodes[node_name]

        if node.op in ("input", "const"):
            continue

        if node.op in ("add", "sub", "mul", "div"):
            left = graph.nodes[node.operands[0]]
            right = graph.nodes[node.operands[1]]

            # 1. Check physical domain containment for expanded intervals
            exp_l = left.expanded_interval
            exp_r = right.expanded_interval
            if not node.domain_in.contains(exp_l):
                raise ValueError(
                    f"Physical domain violation at node '{node.name}': left operand {exp_l} not in domain {node.domain_in}"
                )
            if not node.domain_in.contains(exp_r):
                raise ValueError(
                    f"Physical domain violation at node '{node.name}': right operand {exp_r} not in domain {node.domain_in}"
                )

            # 2. Compute ideal interval and composed error
            ea = left.composed_error
            eb = right.composed_error
            ma = left.ideal_interval.magnitude
            mb = right.ideal_interval.magnitude

            if node.op == "add":
                node.ideal_interval = left.ideal_interval.add(right.ideal_interval)
                node.composed_error = ea + eb + node.local_error
            elif node.op == "sub":
                node.ideal_interval = left.ideal_interval.sub(right.ideal_interval)
                node.composed_error = ea + eb + node.local_error
            elif node.op == "mul":
                node.ideal_interval = left.ideal_interval.mul(right.ideal_interval)
                # Formally proven Lumiris multiplication error theorem:
                node.composed_error = (ea * mb) + (ma * eb) + (ea * eb) + node.local_error
            elif node.op == "div":
                m = right.ideal_interval.min_magnitude
                # Strict Lumiris requirement: minimum denominator m > 0 and error eb < m
                if m <= 0.0:
                    raise ValueError(f"Unsafe division at '{node.name}': denominator interval {right.ideal_interval} contains zero")
                if eb >= m:
                    raise ValueError(
                        f"Uncertain divisor at '{node.name}': error eb ({eb}) >= minimum denominator ({m})"
                    )
                node.ideal_interval = left.ideal_interval.div(right.ideal_interval)
                node.composed_error = ((ea * mb) + (ma * eb)) / (m * (m - eb)) + node.local_error

        elif node.op == "gemm":
            weight_node = graph.nodes[node.operands[0]]
            in_node = graph.nodes[node.operands[1]]
            exp_in = in_node.expanded_interval
            if not node.domain_in.contains(exp_in):
                raise ValueError(
                    f"GEMM domain violation at '{node.name}': input {exp_in} not in domain {node.domain_in}"
                )
            # Matrix-vector error propagation
            shape = node.metadata["shape"]
            m_rows, n_cols = shape
            ea = in_node.composed_error
            node.ideal_interval = in_node.ideal_interval.mul(weight_node.ideal_interval)
            node.composed_error = (n_cols * ea * weight_node.ideal_interval.magnitude) + node.local_error

        elif node.op == "transcendental":
            in_node = graph.nodes[node.operands[0]]
            exp_in = in_node.expanded_interval
            if not node.domain_in.contains(exp_in):
                raise ValueError(
                    f"Transcendental domain violation at '{node.name}': input {exp_in} not in domain {node.domain_in}"
                )
            # Composed error = input uncertainty * Lipschitz constant + approximation truncation error
            func_name = node.metadata["func"]
            # Lipschitz bounds for standard activations
            lipschitz = 1.0  # Default for tanh, sigmoid, sin, cos
            if func_name == "exp":
                lipschitz = math.exp(in_node.ideal_interval.hi)
            node.composed_error = (in_node.composed_error * lipschitz) + node.local_error
            # Approximate ideal range
            node.ideal_interval = node.domain_out

        # Output domain check
        if not node.domain_out.contains(node.expanded_interval):
            raise ValueError(
                f"Saturation violation at '{node.name}': expanded output {node.expanded_interval} exceeds output domain {node.domain_out}"
            )

    # Validate output tolerance
    if graph.output_node is None:
        raise ValueError("Graph has no declared output node")
    out_node = graph.nodes[graph.output_node]
    if out_node.composed_error > graph.requested_tolerance:
        raise ValueError(
            f"Requested tolerance violated: node '{out_node.name}' error ({out_node.composed_error:.8f}) > tolerance ({graph.requested_tolerance:.8f})"
        )

    return {
        "status": "PASS",
        "output_node": graph.output_node,
        "composed_error": out_node.composed_error,
        "requested_tolerance": graph.requested_tolerance,
        "ideal_interval": (out_node.ideal_interval.lo, out_node.ideal_interval.hi),
        "total_nodes": len(graph.nodes),
    }
