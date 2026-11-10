import Lumiris.Core.Approx

/-!
# Bounded, per-device contracts

Unlike the legacy globally quantified `Realization`, these contracts only hold on
specified physical domains. Each operand's *actual*, not merely ideal, value must
be in the domain. Constants and inputs may both have error. No stochastic claim
is made. Model calibration remains an explicit external assumption.
-/
noncomputable section
namespace Lumiris.Bounded

structure Value where
  ideal : ℝ
  actual : ℝ
  range : Range
  error : ℝ
  error_nonneg : 0 ≤ error
  ideal_mem : range.contains ideal
  close : |actual - ideal| ≤ error

def Value.actualRange (v : Value) : Range :=
  ⟨v.range.lo - v.error, v.range.hi + v.error, by linarith [v.range.le, v.error_nonneg]⟩

theorem Value.actual_mem (v : Value) : v.actualRange.contains v.actual := by
  obtain ⟨hlo, hhi⟩ := v.ideal_mem
  obtain ⟨he0, he1⟩ := abs_le.mp v.close
  constructor <;> dsimp [Value.actualRange, Range.contains] <;> linarith

structure Contract (op : ℝ → ℝ → ℝ) where
  inputLeft : Range
  inputRight : Range
  output : Range
  transfer : ℝ → ℝ → ℝ
  localError : ℝ
  localError_nonneg : 0 ≤ localError
  spec : ∀ x y, inputLeft.contains x → inputRight.contains y →
    |transfer x y - op x y| ≤ localError
  safe : ∀ x y, inputLeft.contains x → inputRight.contains y → output.contains (transfer x y)

/-- The common composition step. Physical-domain membership is an explicit obligation. -/
theorem compose {op : ℝ → ℝ → ℝ} (c : Contract op) (a b : Value)
    (ha : c.inputLeft.contains a.actual) (hb : c.inputRight.contains b.actual)
    {propagated : ℝ}
    (hp : |op a.actual b.actual - op a.ideal b.ideal| ≤ propagated) :
    |c.transfer a.actual b.actual - op a.ideal b.ideal| ≤ propagated + c.localError := by
  calc
    _ ≤ |c.transfer a.actual b.actual - op a.actual b.actual| +
        |op a.actual b.actual - op a.ideal b.ideal| := abs_sub_le _ _ _
    _ ≤ c.localError + propagated := add_le_add (c.spec _ _ ha hb) hp
    _ = _ := add_comm _ _

theorem add (c : Contract (· + ·)) (a b : Value)
    (ha : c.inputLeft.contains a.actual) (hb : c.inputRight.contains b.actual) :
    |c.transfer a.actual b.actual - (a.ideal + b.ideal)| ≤ a.error + b.error + c.localError := by
  apply compose c a b ha hb
  exact le_trans (ErrProp.add _ _ _ _) (add_le_add a.close b.close)

theorem sub (c : Contract (· - ·)) (a b : Value)
    (ha : c.inputLeft.contains a.actual) (hb : c.inputRight.contains b.actual) :
    |c.transfer a.actual b.actual - (a.ideal - b.ideal)| ≤ a.error + b.error + c.localError := by
  apply compose c a b ha hb
  exact le_trans (ErrProp.sub _ _ _ _) (add_le_add a.close b.close)

theorem mul (c : Contract (· * ·)) (a b : Value)
    (ha : c.inputLeft.contains a.actual) (hb : c.inputRight.contains b.actual) :
    |c.transfer a.actual b.actual - a.ideal * b.ideal| ≤
      a.error * b.range.mag + a.range.mag * b.error + a.error * b.error + c.localError := by
  apply compose c a b ha hb
  have hMa := Range.abs_le_mag a.ideal_mem
  have hMb := Range.abs_le_mag b.ideal_mem
  have h1 := mul_le_mul a.close hMb (abs_nonneg _) a.error_nonneg
  have h2 := mul_le_mul hMa b.close (abs_nonneg _) a.range.mag_nonneg
  have h3 := mul_le_mul a.close b.close (abs_nonneg _) a.error_nonneg
  have h := ErrProp.mul a.ideal a.actual b.ideal b.actual
  linarith

/-- Division requires separation of the *perturbed* denominator from zero. -/
theorem div (c : Contract (· / ·)) (a b : Value)
    (ha : c.inputLeft.contains a.actual) (hb : c.inputRight.contains b.actual)
    (hsafe : b.error < b.range.minMag) :
    |c.transfer a.actual b.actual - a.ideal / b.ideal| ≤
      (a.error * b.range.mag + a.range.mag * b.error) /
        (b.range.minMag * (b.range.minMag - b.error)) + c.localError := by
  apply compose c a b ha hb
  exact ErrProp.div_bound (Range.abs_le_mag a.ideal_mem) (Range.abs_le_mag b.ideal_mem)
    a.close b.close (Range.minMag_le_abs b.ideal_mem) hsafe a.error_nonneg b.error_nonneg

end Lumiris.Bounded
