import Lumiris.Core.Encoding
import Lumiris.Core.Semantics
import Lumiris.Physics.Control

noncomputable section
namespace Lumiris.Tests

example : Dim.volt.mul Dim.ampere = Dim.watt := by decide
example : (Range.mul ⟨1, 2, by norm_num⟩ ⟨1, 2, by norm_num⟩).lo = 1 := by
  norm_num [Range.mul]
example : (Range.div ⟨1, 1, by norm_num⟩ ⟨1, 4, by norm_num⟩).lo = 1 / 4 := by
  norm_num [Range.div, Range.mul, Range.reciprocal]
example : (Range.div ⟨1, 1, by norm_num⟩ ⟨-4, -1, by norm_num⟩).hi = -(1 / 4) := by
  norm_num [Range.div, Range.mul, Range.reciprocal]
example (x : ℝ) : (Encoding.optPow 1 (by norm_num)).dec
    ((Encoding.optPow 1 (by norm_num)).enc x) = x := by
  simp [Encoding.optPow, Encoding.scaled]
example : ¬ (Range.sym 1 (by norm_num)).minMag > 0 := by
  norm_num [Range.minMag, Range.sym]

end Lumiris.Tests
