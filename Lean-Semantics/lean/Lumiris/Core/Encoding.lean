import Lumiris.Core.Range
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic

/-!
# Number encodings

A real number is carried by a physical quantity (optical power, field amplitude, voltage,
conductance, ...). An `Encoding` is a pair `enc/dec` that round-trips exactly on its domain,
together with the physical constraints of the carrier (e.g. power is non-negative).
-/

noncomputable section

namespace Lumiris

/-- An encoding of reals (on `domain`) into a physical carrier type `Q`. -/
structure Encoding (Q : Type) where
  domain : Range
  enc : ℝ → Q
  dec : Q → ℝ
  dec_enc : ∀ x, domain.contains x → dec (enc x) = x

namespace Encoding

/-- Linear scaling into a carrier with full-scale value `fs` (e.g. `1.0 ↦ 1 mW`). -/
noncomputable def scaled (fs : ℝ) (hfs : 0 < fs) (domain : Range) : Encoding ℝ where
  domain := domain
  enc x := x * fs
  dec q := q / fs
  dec_enc x _ := by field_simp [ne_of_gt hfs]

/-- Unipolar optical power: domain `[0, 1]`, carrier `P ∈ [0, Pmax]`. The carrier is never
negative on the domain. -/
noncomputable def optPow (Pmax : ℝ) (h : 0 < Pmax) : Encoding ℝ :=
  scaled Pmax h ⟨0, 1, by norm_num⟩

theorem optPow_nonneg (Pmax : ℝ) (h : 0 < Pmax) {x : ℝ}
    (hx : (optPow Pmax h).domain.contains x) : 0 ≤ (optPow Pmax h).enc x := by
  obtain ⟨h0, _⟩ := hx
  simp only [optPow, scaled]
  exact mul_nonneg h0 h.le

theorem optPow_le_max (Pmax : ℝ) (h : 0 < Pmax) {x : ℝ}
    (hx : (optPow Pmax h).domain.contains x) : (optPow Pmax h).enc x ≤ Pmax := by
  have hx1 : x ≤ 1 := hx.2
  change x * Pmax ≤ Pmax
  nlinarith

/-- Finite-resolution carriers need an approximate round trip, not an impossible exact inverse. -/
structure ApproxEncoding (Q : Type) where
  domain : Range
  enc : ℝ → Q
  dec : Q → ℝ
  error : ℝ
  error_nonneg : 0 ≤ error
  roundtrip : ∀ x, domain.contains x → |dec (enc x) - x| ≤ error

/-- Differential (signed) encoding into a pair of non-negative carriers,
`x = x⁺ − x⁻` (balanced photodetection, `G⁺ − G⁻` crossbar columns). -/
noncomputable def differential (m : ℝ) (hm : 0 ≤ m) : Encoding (ℝ × ℝ) where
  domain := Range.sym m hm
  enc x := (max x 0, max (-x) 0)
  dec p := p.1 - p.2
  dec_enc x _ := by
    show max x 0 - max (-x) 0 = x
    rcases le_total 0 x with hx | hx
    · rw [max_eq_left hx, max_eq_right (by linarith)]; ring
    · rw [max_eq_right hx, max_eq_left (by linarith)]; ring

theorem differential_nonneg (m : ℝ) (hm : 0 ≤ m) (x : ℝ) :
    0 ≤ ((differential m hm).enc x).1 ∧ 0 ≤ ((differential m hm).enc x).2 :=
  ⟨le_max_right _ _, le_max_right _ _⟩

/-- Conductance encoding: a weight `w ∈ [0, 1]` is stored as `G = Gmin + w·(Gmax − Gmin)`,
which always lies in the physically allowed window `[Gmin, Gmax]`. -/
noncomputable def conductance (Gmin Gmax : ℝ) (_h0 : 0 ≤ Gmin) (h : Gmin < Gmax) : Encoding ℝ where
  domain := ⟨0, 1, by norm_num⟩
  enc w := Gmin + w * (Gmax - Gmin)
  dec G := (G - Gmin) / (Gmax - Gmin)
  dec_enc w _ := by
    have : Gmax - Gmin ≠ 0 := by linarith
    field_simp

theorem conductance_in_window (Gmin Gmax : ℝ) (h0 : 0 ≤ Gmin) (h : Gmin < Gmax) {w : ℝ}
    (hw : (conductance Gmin Gmax h0 h).domain.contains w) :
    Gmin ≤ (conductance Gmin Gmax h0 h).enc w ∧ (conductance Gmin Gmax h0 h).enc w ≤ Gmax := by
  obtain ⟨h0, h1⟩ := hw
  simp only [conductance]
  constructor <;> nlinarith

/-- A closed analysis envelope, NOT an invertible phase encoding: 0 and 2π coincide. -/
def phaseDomain : Range := ⟨0, 2 * Real.pi, by positivity⟩

/-- The half-open branch used when a unique phase representative is required. -/
def PhaseAngle := {φ : ℝ // 0 ≤ φ ∧ φ < 2 * Real.pi}

end Encoding

end Lumiris
