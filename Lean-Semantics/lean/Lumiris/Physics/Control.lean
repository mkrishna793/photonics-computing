import Lumiris.Core.Units
import Lumiris.Core.Approx
import Lumiris.Physics.Photonic

noncomputable section
namespace Lumiris.Control

/-- A unipolar voltage DAC. `levels` is 2^bits in the concrete backend. -/
structure VoltageDAC where
  levels : ℕ
  levels_ge_two : 2 ≤ levels
  fullScale : Volt
  fullScale_pos : 0 < fullScale.val

def VoltageDAC.voltage (d : VoltageDAC) (code : Fin d.levels) : Volt :=
  ⟨(code.val : ℝ) * d.fullScale.val / ((d.levels - 1 : ℕ) : ℝ)⟩

theorem VoltageDAC.safe (d : VoltageDAC) (code : Fin d.levels) :
    0 ≤ (d.voltage code).val ∧ (d.voltage code).val ≤ d.fullScale.val := by
  have hn : 0 < d.levels - 1 := by have := d.levels_ge_two; omega
  have hd : (0 : ℝ) < ((d.levels - 1 : ℕ) : ℝ) := by exact_mod_cast hn
  have hc : code.val ≤ d.levels - 1 := by have := code.isLt; omega
  have hc' : (code.val : ℝ) ≤ ((d.levels - 1 : ℕ) : ℝ) := by exact_mod_cast hc
  constructor
  · exact div_nonneg (mul_nonneg (Nat.cast_nonneg _) d.fullScale_pos.le) hd.le
  · change (code.val : ℝ) * d.fullScale.val / ((d.levels - 1 : ℕ) : ℝ) ≤ _
    apply (div_le_iff₀ hd).mpr
    nlinarith [d.fullScale_pos]

/-- End-to-end static-weight MZI error, including input conversion error.
The cosine/weight premise must be established for the calibrated phase interval.
The Python checker currently supplies that premise via exact Taylor interval arithmetic;
its Taylor algorithm is not yet linked to this theorem by a kernel-checked proof. -/
theorem mzi_error {theta weight x actual delta inputError magnitude : ℝ}
    (hd : 0 ≤ delta) (he : 0 ≤ inputError)
    (ht : |Photonic.mziAmp theta - weight| ≤ delta)
    (hx : |x| ≤ magnitude) (hi : |actual - x| ≤ inputError) :
    |Photonic.mziAmp theta * actual - weight * x| ≤
      |weight| * inputError + delta * (magnitude + inputError) := by
  have h1 := mul_le_mul ht hx (abs_nonneg _) hd
  have h2 := mul_le_mul (le_refl |weight|) hi (abs_nonneg _) (abs_nonneg weight)
  have h3 := mul_le_mul ht hi (abs_nonneg _) hd
  have h := ErrProp.mul weight (Photonic.mziAmp theta) x actual
  nlinarith

end Lumiris.Control
