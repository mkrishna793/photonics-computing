import Mathlib.Data.Real.Basic
import Mathlib.Tactic

/-!
# Ranges (interval arithmetic for range analysis)

Analog values are bounded (T ≤ 1, G ∈ [Gmin, Gmax], |V| ≤ Vmax). Every L2 value carries a
`Range`; lowering inserts scaling so intermediate values fit the hardware.
-/

noncomputable section

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

/-- A scalar multiple attains its extrema at an interval endpoint. -/
theorem scalar_bounds {lo hi x c : ℝ} (hx : lo ≤ x ∧ x ≤ hi) :
    min (lo * c) (hi * c) ≤ x * c ∧ x * c ≤ max (lo * c) (hi * c) := by
  by_cases hc : 0 ≤ c
  · exact ⟨le_trans (min_le_left _ _) (mul_le_mul_of_nonneg_right hx.1 hc),
      le_trans (mul_le_mul_of_nonneg_right hx.2 hc) (le_max_right _ _)⟩
  · have hc' : c ≤ 0 := le_of_not_ge hc
    exact ⟨le_trans (min_le_right _ _) (mul_le_mul_of_nonpos_right hx.2 hc'),
      le_trans (mul_le_mul_of_nonpos_right hx.1 hc') (le_max_left _ _)⟩

/-- Tight endpoint product range; in particular positive ranges remain positive. -/
def mul (a b : Range) : Range where
  lo := min (min (a.lo * b.lo) (a.hi * b.lo)) (min (a.lo * b.hi) (a.hi * b.hi))
  hi := max (max (a.lo * b.lo) (a.hi * b.lo)) (max (a.lo * b.hi) (a.hi * b.hi))
  le := le_trans (le_trans (min_le_left _ _) (min_le_left _ _))
    (le_trans (le_max_left _ _) (le_max_left _ _))

theorem contains_of_abs_le {m x : ℝ} (hm : 0 ≤ m) (h : |x| ≤ m) : (sym m hm).contains x := by
  obtain ⟨h1, h2⟩ := abs_le.mp h
  exact ⟨h1, h2⟩

theorem contains_mul {a b : Range} {x y : ℝ} (hx : a.contains x) (hy : b.contains y) :
    (a.mul b).contains (x * y) := by
  have h0 := scalar_bounds (c := b.lo) hx
  have h1 := scalar_bounds (c := b.hi) hx
  have h2 := scalar_bounds (c := x) hy
  rw [mul_comm b.lo x, mul_comm b.hi x, mul_comm y x] at h2
  constructor
  · exact le_trans (le_min (le_trans (min_le_left _ _) h0.1)
      (le_trans (min_le_right _ _) h1.1)) h2.1
  · exact le_trans h2.2 (max_le (le_trans h0.2 (le_max_left _ _))
      (le_trans h1.2 (le_max_right _ _)))

/-- Scaling by a constant `c`. -/
def scale (c : ℝ) (a : Range) : Range := (point c).mul a

theorem contains_scale {a : Range} {x : ℝ} (c : ℝ) (hx : a.contains x) :
    (a.scale c).contains (c * x) :=
  contains_mul (contains_point c) hx

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

/-- Tight reciprocal interval. The zero-crossing branch is deliberately uncertifiable. -/
def reciprocal (a : Range) : Range :=
  if hp : 0 < a.lo then
    ⟨1 / a.hi, 1 / a.lo, one_div_le_one_div_of_le hp a.le⟩
  else if hn : a.hi < 0 then
    ⟨1 / a.hi, 1 / a.lo, one_div_le_one_div_of_neg_of_le hn a.le⟩
  else point 0

theorem contains_reciprocal {a : Range} {x : ℝ} (ha : 0 < a.minMag)
    (hx : a.contains x) : a.reciprocal.contains (1 / x) := by
  unfold reciprocal
  split_ifs with hp hn
  · have hxpos : 0 < x := lt_of_lt_of_le hp hx.1
    exact ⟨one_div_le_one_div_of_le hxpos hx.2, one_div_le_one_div_of_le hp hx.1⟩
  · have hxneg : x < 0 := lt_of_le_of_lt hx.2 hn
    exact ⟨one_div_le_one_div_of_neg_of_le hn hx.2,
      one_div_le_one_div_of_neg_of_le hxneg hx.1⟩
  · simp [minMag, hp, hn] at ha

/-- Tight quotient range, meaningful only when `0 < b.minMag`. -/
def div (a b : Range) : Range := a.mul b.reciprocal

theorem contains_div {a b : Range} {x y : ℝ} (hb : 0 < b.minMag)
    (hx : a.contains x) (hy : b.contains y) : (a.div b).contains (x / y) := by
  have h := contains_mul hx (contains_reciprocal hb hy)
  simpa [div, div_eq_mul_inv] using h

end Range

end Lumiris
