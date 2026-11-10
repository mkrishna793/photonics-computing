import Lumiris.Core.Range

/-! Model-level invariants. They do not certify that a fabricated device follows the model. -/
namespace Lumiris.Laws

def Passive (transfer : ℝ → ℝ) : Prop :=
  ∀ P, 0 ≤ P → 0 ≤ transfer P ∧ transfer P ≤ P

theorem passive_scale {T : ℝ} (h0 : 0 ≤ T) (h1 : T ≤ 1) :
    Passive (fun P => T * P) := by
  intro P hP
  exact ⟨mul_nonneg h0 hP, by nlinarith⟩

def ConservesPower (transfer : ℝ → ℝ × ℝ) : Prop :=
  ∀ P, 0 ≤ P → (transfer P).1 + (transfer P).2 = P

end Lumiris.Laws
