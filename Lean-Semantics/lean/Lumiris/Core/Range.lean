import Mathlib.Data.Real.Basic
import Mathlib.Tactic
 
/-!
# Ranges (interval arithmetic for range analysis)
 
Analog values are bounded (T ≤ 1, G ∈ [Gmin, Gmax], |V| ≤ Vmax). Every L2 value carries a
`Range`; lowering inserts scaling so intermediate values fit the hardware.
-/
 
namespace Lumiris
 
/-- A closed real interval `[lo, hi]`. -/
structure Range where
  lo : ℝ
  hi : ℝ
  le : lo ≤ hi
 
namespace Range
 
/-- `r.contains x` : `x ∈ [lo, hi]`. -/
def contains (r : Range) (x : ℝ) : Prop := r.lo ≤ x ∧ x ≤ r.hi
 
def point (c : ℝ) : Range := ⟨c, c, le_rfl⟩
 
theorem contains_point (c : ℝ) : (point c).contains c := ⟨le_rfl, le_rfl⟩
 
/-- Symmetric range `[-m, m]`. -/
def sym (m : ℝ) (hm : 0 ≤ m) : Range := ⟨-m, m, by linarith⟩
 
def add (a b : Range) : Range := ⟨a.lo + b.lo, a.hi + b.hi, by linarith [a.le, b.le]⟩
def neg (a : Range) : Range := ⟨-a.hi, -a.lo, by linarith [a.le]⟩
def sub (a b : Range) : Range := a.add b.neg
 
theorem contains_add {a b : Range} {x y : ℝ} (hx : a.contains x) (hy : b.contains y) :
    (a.add b).contains (x + y) := by
  obtain ⟨h1, h2⟩ := hx; obtain ⟨h3, h4⟩ := hy
  exact ⟨by simp only [add]; linarith, by simp only [add]; linarith⟩
 
theorem contains_neg {a : Range} {x : ℝ} (hx : a.contains x) : a.neg.contains (-x) := by
  obtain ⟨h1, h2⟩ := hx
  exact ⟨by simp only [neg]; linarith, by simp only [neg]; linarith⟩
 
theorem contains_sub {a b : Range} {x y : ℝ} (hx : a.contains x) (hy : b.contains y) :
    (a.sub b).contains (x - y) := by
  have := contains_add hx (contains_neg hy)
  simpa [sub, sub_eq_add_neg] using this
 
/-- Magnitude bound: `|x| ≤ a.mag` for every `x` in the range. -/
def mag (a : Range) : ℝ := max |a.lo| |a.hi|
 
theorem mag_nonneg (a : Range) : 0 ≤ a.mag := le_trans (abs_nonneg _) (le_max_left _ _)
 
theorem abs_le_mag {a : Range} {x : ℝ} (h : a.contains x) : |x| ≤ a.mag := by
  obtain ⟨h1, h2⟩ := h
  unfold mag
  rcases le_total 0 x with hx | hx
  · calc |x| = x := abs_of_nonneg hx
      _ ≤ a.hi := h2
      _ ≤ |a.hi| := le_abs_self _
      _ ≤ max |a.lo| |a.hi| := le_max_right _ _
  · calc |x| = -x := abs_of_nonpos hx
      _ ≤ -a.lo := by linarith
      _ ≤ |a.lo| := neg_le_abs _
      _ ≤ max |a.lo| |a.hi| := le_max_left _ _
 
/-- Product range (symmetric magnitude bound). -/
def mul (a b : Range) : Range := sym (a.mag * b.mag) (mul_nonneg a.mag_nonneg b.mag_nonneg)
 
theorem contains_of_abs_le {m x : ℝ} (hm : 0 ≤ m) (h : |x| ≤ m) : (sym m hm).contains x := by
  obtain ⟨h1, h2⟩ := abs_le.mp h
  exact ⟨h1, h2⟩
 
theorem contains_mul {a b : Range} {x y : ℝ} (hx : a.contains x) (hy : b.contains y) :
    (a.mul b).contains (x * y) := by
  apply contains_of_abs_le
  rw [abs_mul]
  exact mul_le_mul (abs_le_mag hx) (abs_le_mag hy) (abs_nonneg _) a.mag_nonneg
 
/-- Scaling by a constant `c`. -/
def scale (c : ℝ) (a : Range) : Range := sym (|c| * a.mag) (mul_nonneg (abs_nonneg _) a.mag_nonneg)
 
theorem contains_scale {a : Range} {x : ℝ} (c : ℝ) (hx : a.contains x) :
    (a.scale c).contains (c * x) := by
  apply contains_of_abs_le
  rw [abs_mul]
  exact mul_le_mul_of_nonneg_left (abs_le_mag hx) (abs_nonneg _)
 
/-- Lower bound on the magnitude: `a.minMag ≤ |x|` for every `x` in the range.
It is `0` whenever the range touches or crosses zero, so division by such a range is unsafe. -/
def minMag (a : Range) : ℝ := if 0 < a.lo then a.lo else if a.hi < 0 then -a.hi else 0
 
theorem minMag_nonneg (a : Range) : 0 ≤ a.minMag := by
  unfold minMag; split_ifs <;> linarith
 
theorem minMag_le_abs {a : Range} {x : ℝ} (h : a.contains x) : a.minMag ≤ |x| := by
  obtain ⟨h1, h2⟩ := h
  unfold minMag
  split_ifs with hlo hhi
  · calc a.lo ≤ x := h1
      _ ≤ |x| := le_abs_self x
  · calc -a.hi ≤ -x := by linarith
      _ ≤ |x| := neg_le_abs x
  · exact abs_nonneg x
 
/-- A range bounded away from zero is a safe divisor. -/
theorem ne_zero_of_minMag_pos {a : Range} {x : ℝ} (ha : 0 < a.minMag) (h : a.contains x) :
    x ≠ 0 := by
  intro hx
  have := minMag_le_abs h
  rw [hx, abs_zero] at this
  linarith
 
/-- Quotient range, meaningful only when `0 < b.minMag`. -/
noncomputable def div (a b : Range) : Range :=
  sym (a.mag / b.minMag) (div_nonneg a.mag_nonneg b.minMag_nonneg)
 
theorem contains_div {a b : Range} {x y : ℝ} (hb : 0 < b.minMag)
    (hx : a.contains x) (hy : b.contains y) : (a.div b).contains (x / y) := by
  apply contains_of_abs_le
  rw [abs_div]
  have hy' : b.minMag ≤ |y| := minMag_le_abs hy
  exact div_le_div₀ a.mag_nonneg (abs_le_mag hx) hb hy'
 
end Range
 
end Lumiris