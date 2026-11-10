import Lumiris.Core.Range

/-!
# Approximate operations and error composition

Analog hardware never computes exactly. Each of the four core operations is realized by a
physical process whose result is within `ε` of the exact result. These lemmas say how errors
propagate through `+ − × ÷`; they are the foundation of the certified error budget.
-/

namespace Lumiris

/-- An approximate binary operation with a certified error bound on the given input ranges. -/
structure ApproxOp (op : ℝ → ℝ → ℝ) (A B : Range) where
  realize : ℝ → ℝ → ℝ
  err : ℝ
  err_nonneg : 0 ≤ err
  spec : ∀ a b, A.contains a → B.contains b → |realize a b - op a b| ≤ err

namespace ErrProp

theorem add (a a' b b' : ℝ) : |(a' + b') - (a + b)| ≤ |a' - a| + |b' - b| := by
  have h : (a' + b') - (a + b) = (a' - a) + (b' - b) := by ring
  rw [h]; exact abs_add_le _ _

theorem sub (a a' b b' : ℝ) : |(a' - b') - (a - b)| ≤ |a' - a| + |b' - b| := by
  have h : (a' - b') - (a - b) = (a' - a) - (b' - b) := by ring
  rw [h]; exact abs_sub _ _

theorem mul (a a' b b' : ℝ) :
    |a' * b' - a * b| ≤ |a' - a| * |b| + |a| * |b' - b| + |a' - a| * |b' - b| := by
  have h : a' * b' - a * b = (a' - a) * b + a * (b' - b) + (a' - a) * (b' - b) := by ring
  rw [h]
  calc |(a' - a) * b + a * (b' - b) + (a' - a) * (b' - b)|
      ≤ |(a' - a) * b| + |a * (b' - b)| + |(a' - a) * (b' - b)| := le_trans (abs_add_le _ _) (add_le_add_right (abs_add_le _ _) _)
    _ = _ := by rw [abs_mul, abs_mul, abs_mul]

theorem div (a a' b b' : ℝ) (hb : b ≠ 0) (hb' : b' ≠ 0) :
    |a' / b' - a / b| ≤ (|a' - a| * |b| + |a| * |b' - b|) / (|b| * |b'|) := by
  have h : a' / b' - a / b = ((a' - a) * b - a * (b' - b)) / (b * b') := by
    field_simp [hb, hb']; ring
  rw [h, abs_div, abs_mul b b']
  apply div_le_div_of_nonneg_right _ (by positivity)
  calc |(a' - a) * b - a * (b' - b)| ≤ |(a' - a) * b| + |a * (b' - b)| := abs_sub _ _
    _ = _ := by rw [abs_mul, abs_mul]

/-- A perturbed divisor stays away from zero: `|b| ≥ m`, `|b' − b| ≤ e`, `e < m` ⇒ `|b'| ≥ m − e`. -/
theorem abs_perturbed_ge {b b' m e : ℝ} (hm : m ≤ |b|) (he : |b' - b| ≤ e) : m - e ≤ |b'| := by
  have := abs_sub_abs_le_abs_sub b b'
  have h2 : |b - b'| = |b' - b| := abs_sub_comm _ _
  linarith

/-- Monotone bound used in the division case of the budget theorem. -/
theorem div_bound {a a' b b' Ma Mb ea eb m : ℝ}
    (hMa : |a| ≤ Ma) (hMb : |b| ≤ Mb) (hea : |a' - a| ≤ ea) (heb : |b' - b| ≤ eb)
    (hm : m ≤ |b|) (hmeb : eb < m) (hea0 : 0 ≤ ea) (heb0 : 0 ≤ eb) :
    |a' / b' - a / b| ≤ (ea * Mb + Ma * eb) / (m * (m - eb)) := by
  have hmpos : 0 < m := by linarith
  have hb : b ≠ 0 := by
    intro h; rw [h, abs_zero] at hm; linarith
  have hb'abs : m - eb ≤ |b'| := abs_perturbed_ge hm heb
  have hb' : b' ≠ 0 := by
    intro h; rw [h, abs_zero] at hb'abs; linarith
  have hMa0 : 0 ≤ Ma := le_trans (abs_nonneg _) hMa
  have hMb0 : 0 ≤ Mb := le_trans (abs_nonneg _) hMb
  calc |a' / b' - a / b| ≤ (|a' - a| * |b| + |a| * |b' - b|) / (|b| * |b'|) := div a a' b b' hb hb'
    _ ≤ (ea * Mb + Ma * eb) / (m * (m - eb)) := by
        apply div_le_div₀
        · positivity
        · have h1 : |a' - a| * |b| ≤ ea * Mb := mul_le_mul hea hMb (abs_nonneg _) hea0
          have h2 : |a| * |b' - b| ≤ Ma * eb := mul_le_mul hMa heb (abs_nonneg _) hMa0
          linarith
        · have : 0 < m - eb := by linarith
          positivity
        · exact mul_le_mul hm hb'abs (by linarith) (abs_nonneg _)

end ErrProp

end Lumiris
