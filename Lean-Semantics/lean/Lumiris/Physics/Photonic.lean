import Lumiris.Physics.Laws
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Inverse
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Bounds
import Mathlib.LinearAlgebra.Matrix.Notation

/-!
# Photonic branches of the Physics Tree

Each device gives (1) its transfer function, (2) the physical law it obeys, and (3) a
realizability theorem: every target value in the declared range is reachable by some
physical parameter.
-/

noncomputable section
namespace Lumiris
namespace Photonic

open Real

/-! ## Mach–Zehnder interferometer (coherent multiply) -/

/-- Full complex transfer matrix of an MZI with internal phase `θ` and external phase `φ`
(common output phase dropped). -/
def mzi (θ φ : ℝ) : Matrix (Fin 2) (Fin 2) ℂ :=
  !![Complex.exp (φ * Complex.I) * (Real.sin (θ / 2) : ℂ), (Real.cos (θ / 2) : ℂ);
     Complex.exp (φ * Complex.I) * (Real.cos (θ / 2) : ℂ), -(Real.sin (θ / 2) : ℂ)]

/-- Energy conservation: the MZI matrix is unitary (`Mᴴ M = 1`). -/
theorem mzi_unitary (θ φ : ℝ) : (mzi θ φ)ᴴ * mzi θ φ = 1 := by
  have hs : (Real.sin (θ / 2) : ℂ) ^ 2 + (Real.cos (θ / 2) : ℂ) ^ 2 = 1 := by
    have := Real.sin_sq_add_cos_sq (θ / 2)
    exact_mod_cast this
  have he : (starRingEnd ℂ) (Complex.exp (φ * Complex.I)) * Complex.exp (φ * Complex.I) = 1 := by
    rw [← Complex.exp_conj, ← Complex.exp_add]
    simp [Complex.conj_ofReal]
  ext i j
  fin_cases i <;> fin_cases j <;>
    simp [mzi, Matrix.mul_apply, Fin.sum_univ_two, Matrix.conjTranspose_apply] <;>
    first
    | ring
    | linear_combination hs
    | linear_combination ((starRingEnd ℂ) (Complex.exp (φ * Complex.I)) * Complex.exp (φ * Complex.I)) * hs + he

/-- Bar-port amplitude transmission (real): `t(θ) = cos(θ/2)`. -/
def mziAmp (θ : ℝ) : ℝ := Real.cos (θ / 2)

/-- Bar-port power transmission `cos²(θ/2)`, and cross-port `sin²(θ/2)`: they sum to 1. -/
theorem mzi_power_conservation (θ : ℝ) : mziAmp θ ^ 2 + Real.sin (θ / 2) ^ 2 = 1 := by
  unfold mziAmp; rw [add_comm]; exact Real.sin_sq_add_cos_sq _

theorem mziAmp_mem (θ : ℝ) : -1 ≤ mziAmp θ ∧ mziAmp θ ≤ 1 :=
  ⟨Real.neg_one_le_cos _, Real.cos_le_one _⟩

/-- **Realizability of signed multiply.** Every weight `w ∈ [-1, 1]` is reached by the phase
`θ = 2·arccos w ∈ [0, 2π]`. -/
theorem mziAmp_realizable {w : ℝ} (h0 : -1 ≤ w) (h1 : w ≤ 1) :
    ∃ θ, 0 ≤ θ ∧ θ ≤ 2 * Real.pi ∧ mziAmp θ = w := by
  refine ⟨2 * Real.arccos w, ?_, ?_, ?_⟩
  · have := Real.arccos_nonneg w; linarith
  · have := Real.arccos_le_pi w; linarith
  · unfold mziAmp
    rw [show 2 * Real.arccos w / 2 = Real.arccos w by ring]
    exact Real.cos_arccos h0 h1

/-- The MZI realizes `x ↦ w·x` with error only from phase inaccuracy:
`|cos(θ'/2) − cos(θ/2)| ≤ |θ' − θ|/2`. -/
theorem mziAmp_phase_error (θ θ' x : ℝ) :
    |mziAmp θ' * x - mziAmp θ * x| ≤ |θ' - θ| / 2 * |x| := by
  rw [← sub_mul, abs_mul]
  apply mul_le_mul_of_nonneg_right _ (abs_nonneg x)
  unfold mziAmp
  have := Real.abs_cos_sub_cos_le (θ' / 2) (θ / 2)
  calc |Real.cos (θ' / 2) - Real.cos (θ / 2)| ≤ |θ' / 2 - θ / 2| := this
    _ = |θ' - θ| / 2 := by rw [show θ' / 2 - θ / 2 = (θ' - θ) / 2 by ring, abs_div]; norm_num

/-! ## PIN attenuator (incoherent multiply, free-carrier absorption) -/

/-- Beer–Lambert transmission `T = e^{−αL}`. -/
def attenT (α L : ℝ) : ℝ := Real.exp (-(α * L))

theorem attenT_pos (α L : ℝ) : 0 < attenT α L := Real.exp_pos _

theorem attenT_le_one {α L : ℝ} (hα : 0 ≤ α) (hL : 0 ≤ L) : attenT α L ≤ 1 := by
  unfold attenT
  have : -(α * L) ≤ 0 := by nlinarith
  simpa using Real.exp_le_exp.mpr this

/-- The attenuator is passive. -/
theorem attenT_passive {α L : ℝ} (hα : 0 ≤ α) (hL : 0 ≤ L) :
    Laws.Passive (fun P => attenT α L * P) :=
  Laws.passive_scale (attenT_pos α L).le (attenT_le_one hα hL)

/-- **Realizability.** Every `T ∈ (0, 1]` is reached by absorption `αL = −ln T ≥ 0`. -/
theorem attenT_realizable {T : ℝ} (h0 : 0 < T) (h1 : T ≤ 1) :
    ∃ a, 0 ≤ a ∧ attenT a 1 = T := by
  refine ⟨-Real.log T, ?_, ?_⟩
  · have := Real.log_nonpos h0.le h1; linarith
  · unfold attenT; simp [Real.exp_log h0]

/-! ## Microring resonator (wavelength-selective multiply) -/

/-- All-pass ring transmission as a Lorentzian in the detuning `δ = λ − λ_res`,
with intrinsic half-width `γ` and loaded half-width `Γ` (`0 ≤ γ < Γ`). -/
def mrrT (δ γ Γ : ℝ) : ℝ := (δ ^ 2 + γ ^ 2) / (δ ^ 2 + Γ ^ 2)

theorem mrrT_le_one {δ γ Γ : ℝ} (hγ : 0 ≤ γ) (hΓ : γ < Γ) : mrrT δ γ Γ ≤ 1 := by
  unfold mrrT
  have hΓpos : 0 < Γ := by linarith
  have hpos : 0 < δ ^ 2 + Γ ^ 2 := add_pos_of_nonneg_of_pos (sq_nonneg δ) (pow_pos hΓpos 2)
  rw [div_le_one hpos]
  nlinarith

theorem mrrT_nonneg (δ γ Γ : ℝ) : 0 ≤ mrrT δ γ Γ := by unfold mrrT; positivity

/-- Minimum transmission (on resonance) is `γ²/Γ²`; `T = 0` needs critical coupling `γ = 0`. -/
theorem mrrT_ge_floor {δ γ Γ : ℝ} (hγ : 0 ≤ γ) (hΓ : γ < Γ) : γ ^ 2 / Γ ^ 2 ≤ mrrT δ γ Γ := by
  unfold mrrT
  have hΓpos : 0 < Γ := by linarith
  have hpos : 0 < δ ^ 2 + Γ ^ 2 := add_pos_of_nonneg_of_pos (sq_nonneg δ) (pow_pos hΓpos 2)
  rw [div_le_div_iff₀ (pow_pos hΓpos 2) hpos]
  have hsq : γ ^ 2 ≤ Γ ^ 2 := by nlinarith
  nlinarith [mul_le_mul_of_nonneg_left hsq (sq_nonneg δ)]

/-- **Realizability.** Every `T ∈ [γ²/Γ², 1)` is reached by detuning
`δ² = (TΓ² − γ²)/(1 − T)` (two roots `±δ`; the compiler picks one side consistently). -/
theorem mrrT_realizable {T γ Γ : ℝ} (hγ : 0 ≤ γ) (hΓ : γ < Γ)
    (hT0 : γ ^ 2 / Γ ^ 2 ≤ T) (hT1 : T < 1) :
    ∃ δ, 0 ≤ δ ∧ mrrT δ γ Γ = T := by
  have hΓpos : 0 < Γ := by linarith
  have h1T : 0 < 1 - T := by linarith
  have hnum : 0 ≤ T * Γ ^ 2 - γ ^ 2 := by
    rw [div_le_iff₀ (by positivity)] at hT0; linarith
  set d2 := (T * Γ ^ 2 - γ ^ 2) / (1 - T) with hd2
  have hd2nn : 0 ≤ d2 := div_nonneg hnum h1T.le
  refine ⟨Real.sqrt d2, Real.sqrt_nonneg _, ?_⟩
  unfold mrrT
  rw [Real.sq_sqrt hd2nn]
  have hden : d2 + Γ ^ 2 ≠ 0 := by positivity
  apply (div_eq_iff hden).mpr
  dsimp [d2]
  field_simp [ne_of_gt h1T]
  <;> ring

/-! ## Coherent addition, incoherent addition, balanced subtraction, fan-out -/

/-- A 50:50 combiner adds field amplitudes exactly, with a fixed scale `1/√2`. -/
def coherentAdd (E1 E2 : ℝ) : ℝ := (E1 + E2) / Real.sqrt 2

theorem coherentAdd_exact (E1 E2 : ℝ) : coherentAdd E1 E2 * Real.sqrt 2 = E1 + E2 := by
  unfold coherentAdd
  have : Real.sqrt 2 ≠ 0 := by positivity
  field_simp

/-- A π phase shift on one arm turns the combiner into an exact subtractor. -/
theorem coherentSub_exact (E1 E2 : ℝ) :
    coherentAdd E1 (Real.cos Real.pi * E2) * Real.sqrt 2 = E1 - E2 := by
  rw [Real.cos_pi, coherentAdd_exact]; ring

/-- Incoherent (different-wavelength) powers add exactly on one photodetector. -/
def detectorSum {n : ℕ} (P : Fin n → ℝ) : ℝ := ∑ i, P i

/-- Balanced photodetection: `I = R·(P⁺ − P⁻)` — exact signed subtraction with scale `R`. -/
def balanced (R Pplus Pminus : ℝ) : ℝ := R * (Pplus - Pminus)

theorem balanced_exact (R Pplus Pminus : ℝ) (hR : R ≠ 0) :
    balanced R Pplus Pminus / R = Pplus - Pminus := by
  unfold balanced; field_simp

/-- Fan-out is not free: a 1:2 splitter gives each branch half the power, conserving energy. -/
def splitter (P : ℝ) : ℝ × ℝ := (P / 2, P / 2)

theorem splitter_conserves (P : ℝ) : (splitter P).1 + (splitter P).2 = P := by
  dsimp [splitter]
  ring

end Photonic
end Lumiris
end
