import Lumiris.Core.Approx

/-!
# L2 Core Analog Algebra: syntax, exact semantics, realized semantics, certified error budget

`Expr` is the abstract core: constants, inputs, and the four field operations `+ − × ÷`.
`eval` is the exact mathematical meaning. `realEval` is what analog hardware computes when
each operation is realized by an approximate physical process (`Realization`).
The main theorem `budget_sound` proves that the compiler-computed `errBound` really bounds
the difference, and `range_sound` proves that range analysis is sound — the two facts a
certificate checker needs.
-/

noncomputable section

namespace Lumiris

inductive Expr where
  | const : ℝ → Expr
  | var   : ℕ → Expr
  | add   : Expr → Expr → Expr
  | sub   : Expr → Expr → Expr
  | mul   : Expr → Expr → Expr
  | div   : Expr → Expr → Expr

namespace Expr

/-- Exact (digital, infinite-precision) meaning. -/
noncomputable def eval (env : ℕ → ℝ) : Expr → ℝ
  | const c => c
  | var i   => env i
  | add a b => a.eval env + b.eval env
  | sub a b => a.eval env - b.eval env
  | mul a b => a.eval env * b.eval env
  | div a b => a.eval env / b.eval env

/-- Range analysis under a typing context `Γ` giving the range of each input. -/
noncomputable def range (Γ : ℕ → Range) : Expr → Range
  | const c => Range.point c
  | var i   => Γ i
  | add a b => (a.range Γ).add (b.range Γ)
  | sub a b => (a.range Γ).sub (b.range Γ)
  | mul a b => (a.range Γ).mul (b.range Γ)
  | div a b => (a.range Γ).div (b.range Γ)

/-- Every divisor is bounded away from zero (checked by Z3 per instance). -/
def divSafe (Γ : ℕ → Range) : Expr → Prop
  | const _ => True
  | var _   => True
  | add a b => a.divSafe Γ ∧ b.divSafe Γ
  | sub a b => a.divSafe Γ ∧ b.divSafe Γ
  | mul a b => a.divSafe Γ ∧ b.divSafe Γ
  | div a b => a.divSafe Γ ∧ b.divSafe Γ ∧ 0 < (b.range Γ).minMag

theorem range_sound {Γ : ℕ → Range} {env : ℕ → ℝ} (henv : ∀ i, (Γ i).contains (env i)) :
    ∀ e : Expr, e.divSafe Γ → (e.range Γ).contains (e.eval env)
  | const c, _ => Range.contains_point c
  | var i, _ => henv i
  | add a b, ⟨ha, hb⟩ => Range.contains_add (range_sound henv a ha) (range_sound henv b hb)
  | sub a b, ⟨ha, hb⟩ => Range.contains_sub (range_sound henv a ha) (range_sound henv b hb)
  | mul a b, ⟨ha, hb⟩ => Range.contains_mul (range_sound henv a ha) (range_sound henv b hb)
  | div a b, ⟨ha, hb, hsafe⟩ =>
      Range.contains_div hsafe (range_sound henv a ha) (range_sound henv b hb)

end Expr

/-- Legacy idealized global realization. Real devices should use `Bounded.Contract`.
Each operation is computed by a process that is
within a fixed `ε` of the exact operation. Inputs may also be encoded with error `εvar`. -/
structure Realization where
  addR : ℝ → ℝ → ℝ
  subR : ℝ → ℝ → ℝ
  mulR : ℝ → ℝ → ℝ
  divR : ℝ → ℝ → ℝ
  εadd : ℝ
  εsub : ℝ
  εmul : ℝ
  εdiv : ℝ
  εvar : ℕ → ℝ
  εadd_nonneg : 0 ≤ εadd
  εsub_nonneg : 0 ≤ εsub
  εmul_nonneg : 0 ≤ εmul
  εdiv_nonneg : 0 ≤ εdiv
  εvar_nonneg : ∀ i, 0 ≤ εvar i
  addR_spec : ∀ a b, |addR a b - (a + b)| ≤ εadd
  subR_spec : ∀ a b, |subR a b - (a - b)| ≤ εsub
  mulR_spec : ∀ a b, |mulR a b - a * b| ≤ εmul
  divR_spec : ∀ a b, b ≠ 0 → |divR a b - a / b| ≤ εdiv

namespace Expr

/-- What the analog hardware computes. -/
noncomputable def realEval (ρ : Realization) (env' : ℕ → ℝ) : Expr → ℝ
  | const c => c
  | var i   => env' i
  | add a b => ρ.addR (a.realEval ρ env') (b.realEval ρ env')
  | sub a b => ρ.subR (a.realEval ρ env') (b.realEval ρ env')
  | mul a b => ρ.mulR (a.realEval ρ env') (b.realEval ρ env')
  | div a b => ρ.divR (a.realEval ρ env') (b.realEval ρ env')

/-- Compiler-computed error budget. -/
noncomputable def errBound (ρ : Realization) (Γ : ℕ → Range) : Expr → ℝ
  | const _ => 0
  | var i   => ρ.εvar i
  | add a b => a.errBound ρ Γ + b.errBound ρ Γ + ρ.εadd
  | sub a b => a.errBound ρ Γ + b.errBound ρ Γ + ρ.εsub
  | mul a b =>
      a.errBound ρ Γ * (b.range Γ).mag + (a.range Γ).mag * b.errBound ρ Γ
        + a.errBound ρ Γ * b.errBound ρ Γ + ρ.εmul
  | div a b =>
      (a.errBound ρ Γ * (b.range Γ).mag + (a.range Γ).mag * b.errBound ρ Γ)
        / ((b.range Γ).minMag * ((b.range Γ).minMag - b.errBound ρ Γ)) + ρ.εdiv

/-- Realized divisors stay away from zero: the accumulated error on a divisor is smaller than
its guaranteed magnitude. Checked by Z3 per instance. -/
noncomputable def budgetSafe (ρ : Realization) (Γ : ℕ → Range) : Expr → Prop
  | const _ => True
  | var _   => True
  | add a b => a.budgetSafe ρ Γ ∧ b.budgetSafe ρ Γ
  | sub a b => a.budgetSafe ρ Γ ∧ b.budgetSafe ρ Γ
  | mul a b => a.budgetSafe ρ Γ ∧ b.budgetSafe ρ Γ
  | div a b => a.budgetSafe ρ Γ ∧ b.budgetSafe ρ Γ ∧ b.errBound ρ Γ < (b.range Γ).minMag

theorem errBound_nonneg (ρ : Realization) (Γ : ℕ → Range) :
    ∀ e : Expr, e.budgetSafe ρ Γ → 0 ≤ e.errBound ρ Γ
  | const _, _ => le_rfl
  | var i, _ => ρ.εvar_nonneg i
  | add a b, ⟨ha, hb⟩ => by
      have := errBound_nonneg ρ Γ a ha; have := errBound_nonneg ρ Γ b hb
      have := ρ.εadd_nonneg; simp only [errBound]; linarith
  | sub a b, ⟨ha, hb⟩ => by
      have := errBound_nonneg ρ Γ a ha; have := errBound_nonneg ρ Γ b hb
      have := ρ.εsub_nonneg; simp only [errBound]; linarith
  | mul a b, ⟨ha, hb⟩ => by
      have h1 := errBound_nonneg ρ Γ a ha; have h2 := errBound_nonneg ρ Γ b hb
      have := ρ.εmul_nonneg
      have := (a.range Γ).mag_nonneg; have := (b.range Γ).mag_nonneg
      simp only [errBound]; positivity
  | div a b, ⟨ha, hb, hs⟩ => by
      have h1 := errBound_nonneg ρ Γ a ha; have h2 := errBound_nonneg ρ Γ b hb
      have := ρ.εdiv_nonneg
      have := (a.range Γ).mag_nonneg; have := (b.range Γ).mag_nonneg
      have h3 : 0 < (b.range Γ).minMag - b.errBound ρ Γ := by linarith
      have h4 : 0 < (b.range Γ).minMag := by linarith
      simp only [errBound]; positivity

/-- **Certified error budget.** If inputs lie in their declared ranges, encoded inputs are
within `εvar` of the true inputs, divisors are safe, then the analog result is within
`errBound` of the exact mathematical result. -/
theorem budget_sound (ρ : Realization) {Γ : ℕ → Range} {env env' : ℕ → ℝ}
    (henv : ∀ i, (Γ i).contains (env i)) (henv' : ∀ i, |env' i - env i| ≤ ρ.εvar i) :
    ∀ e : Expr, e.divSafe Γ → e.budgetSafe ρ Γ →
      |e.realEval ρ env' - e.eval env| ≤ e.errBound ρ Γ
  | const c, _, _ => by simp [realEval, eval, errBound]
  | var i, _, _ => henv' i
  | add a b, ⟨da, db⟩, ⟨ba, bb⟩ => by
      have ha := budget_sound ρ henv henv' a da ba
      have hb := budget_sound ρ henv henv' b db bb
      simp only [realEval, eval, errBound]
      calc |ρ.addR (a.realEval ρ env') (b.realEval ρ env') - (a.eval env + b.eval env)|
          ≤ |ρ.addR (a.realEval ρ env') (b.realEval ρ env')
                - (a.realEval ρ env' + b.realEval ρ env')|
            + |(a.realEval ρ env' + b.realEval ρ env') - (a.eval env + b.eval env)| :=
              abs_sub_le _ _ _
        _ ≤ ρ.εadd + (|a.realEval ρ env' - a.eval env| + |b.realEval ρ env' - b.eval env|) :=
              add_le_add (ρ.addR_spec _ _) (ErrProp.add _ _ _ _)
        _ ≤ _ := by linarith
  | sub a b, ⟨da, db⟩, ⟨ba, bb⟩ => by
      have ha := budget_sound ρ henv henv' a da ba
      have hb := budget_sound ρ henv henv' b db bb
      simp only [realEval, eval, errBound]
      calc |ρ.subR (a.realEval ρ env') (b.realEval ρ env') - (a.eval env - b.eval env)|
          ≤ |ρ.subR (a.realEval ρ env') (b.realEval ρ env')
                - (a.realEval ρ env' - b.realEval ρ env')|
            + |(a.realEval ρ env' - b.realEval ρ env') - (a.eval env - b.eval env)| :=
              abs_sub_le _ _ _
        _ ≤ ρ.εsub + (|a.realEval ρ env' - a.eval env| + |b.realEval ρ env' - b.eval env|) :=
              add_le_add (ρ.subR_spec _ _) (ErrProp.sub _ _ _ _)
        _ ≤ _ := by linarith
  | mul a b, ⟨da, db⟩, ⟨ba, bb⟩ => by
      have ha := budget_sound ρ henv henv' a da ba
      have hb := budget_sound ρ henv henv' b db bb
      have hMa := Range.abs_le_mag (range_sound henv a da)
      have hMb := Range.abs_le_mag (range_sound henv b db)
      have hea0 := errBound_nonneg ρ Γ a ba
      have heb0 := errBound_nonneg ρ Γ b bb
      simp only [realEval, eval, errBound]
      calc |ρ.mulR (a.realEval ρ env') (b.realEval ρ env') - a.eval env * b.eval env|
          ≤ |ρ.mulR (a.realEval ρ env') (b.realEval ρ env')
                - a.realEval ρ env' * b.realEval ρ env'|
            + |a.realEval ρ env' * b.realEval ρ env' - a.eval env * b.eval env| :=
              abs_sub_le _ _ _
        _ ≤ ρ.εmul + (|a.realEval ρ env' - a.eval env| * |b.eval env|
              + |a.eval env| * |b.realEval ρ env' - b.eval env|
              + |a.realEval ρ env' - a.eval env| * |b.realEval ρ env' - b.eval env|) :=
              add_le_add (ρ.mulR_spec _ _) (ErrProp.mul _ _ _ _)
        _ ≤ ρ.εmul + (a.errBound ρ Γ * (b.range Γ).mag + (a.range Γ).mag * b.errBound ρ Γ
              + a.errBound ρ Γ * b.errBound ρ Γ) := by
              have h1 := mul_le_mul ha hMb (abs_nonneg _) hea0
              have h2 := mul_le_mul hMa hb (abs_nonneg _) (le_trans (abs_nonneg _) hMa)
              have h3 := mul_le_mul ha hb (abs_nonneg _) hea0
              linarith
        _ = _ := by ring
  | div a b, ⟨da, db, dsafe⟩, ⟨ba, bb, bsafe⟩ => by
      have ha := budget_sound ρ henv henv' a da ba
      have hb := budget_sound ρ henv henv' b db bb
      have hMa := Range.abs_le_mag (range_sound henv a da)
      have hMb := Range.abs_le_mag (range_sound henv b db)
      have hm := Range.minMag_le_abs (range_sound henv b db)
      have hea0 := errBound_nonneg ρ Γ a ba
      have heb0 := errBound_nonneg ρ Γ b bb
      have hb'ne : b.realEval ρ env' ≠ 0 := by
        intro h
        have := ErrProp.abs_perturbed_ge hm hb
        rw [h, abs_zero] at this
        linarith
      simp only [realEval, eval, errBound]
      calc |ρ.divR (a.realEval ρ env') (b.realEval ρ env') - a.eval env / b.eval env|
          ≤ |ρ.divR (a.realEval ρ env') (b.realEval ρ env')
                - a.realEval ρ env' / b.realEval ρ env'|
            + |a.realEval ρ env' / b.realEval ρ env' - a.eval env / b.eval env| :=
              abs_sub_le _ _ _
        _ ≤ ρ.εdiv + (a.errBound ρ Γ * (b.range Γ).mag + (a.range Γ).mag * b.errBound ρ Γ)
              / ((b.range Γ).minMag * ((b.range Γ).minMag - b.errBound ρ Γ)) :=
              add_le_add (ρ.divR_spec _ _ hb'ne)
                (ErrProp.div_bound hMa hMb ha hb hm bsafe hea0 heb0)
        _ = _ := by ring

end Expr

end Lumiris
