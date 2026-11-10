import Lumiris.Core.Range
 
/-!
# Number encodings
 
A real number is carried by a physical quantity (optical power, field amplitude, voltage,
conductance, ...). An `Encoding` is a pair `enc/dec` that round-trips exactly on its domain,
together with the physical constraints of the carrier (e.g. power is non-negative).
-/
 
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
  dec_enc x _ := by field_simp
 
/-- Unipolar optical power: domain `[0, 1]`, carrier `P ∈ [0, Pmax]`. The carrier is never
negative on the domain. -/
noncomputable def optPow (Pmax : ℝ) (h : 0 < Pmax) : Encoding ℝ :=
  scaled Pmax h ⟨0, 1, by norm_num⟩
 
theorem optPow_nonneg (Pmax : ℝ) (h : 0 < Pmax) {x : ℝ}
    (hx : (optPow Pmax h).domain.contains x) : 0 ≤ (optPow Pmax h).enc x := by
  obtain ⟨h0, _⟩ := hx
  simp only [optPow, scaled]
  exact mul_nonneg h0 h.le
 
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
noncomputable def conductance (Gmin Gmax : ℝ) (h : Gmin < Gmax) : Encoding ℝ where
  domain := ⟨0, 1, by norm_num⟩
  enc w := Gmin + w * (Gmax - Gmin)
  dec G := (G - Gmin) / (Gmax - Gmin)
  dec_enc w _ := by
    have : Gmax - Gmin ≠ 0 := by linarith
    field_simp
 
theorem conductance_in_window (Gmin Gmax : ℝ) (h : Gmin < Gmax) {w : ℝ}
    (hw : (conductance Gmin Gmax h).domain.contains w) :
    Gmin ≤ (conductance Gmin Gmax h).enc w ∧ (conductance Gmin Gmax h).enc w ≤ Gmax := by
  obtain ⟨h0, h1⟩ := hw
  simp only [conductance]
  constructor <;> nlinarith
 
/-- Phase encoding of an angle: `φ ↦ e^{iφ}` is only invertible modulo `2π`, so the domain
is `[0, 2π)`-shaped (we use the closed `[0, 2π]` range and the branch `[0, 2π)` in control). -/
def phaseDomain : Range := ⟨0, 2 * Real.pi, by positivity⟩
 
end Encoding
 
end Lumiris