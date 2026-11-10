import Mathlib.Data.Real.Basic
import Mathlib.Tactic
 
/-!
# Physical units as types
 
Every physical quantity the compiler manipulates carries its SI dimension in its type.
Adding a voltage to a wavelength is a type error, not a runtime surprise.
-/
 
namespace Lumiris
 
/-- SI dimension exponents: length, mass, time, electric current, temperature. -/
structure Dim where
  L : ℤ := 0
  M : ℤ := 0
  T : ℤ := 0
  I : ℤ := 0
  Θ : ℤ := 0
  deriving DecidableEq, Repr
 
namespace Dim
 
def mul (a b : Dim) : Dim := ⟨a.L + b.L, a.M + b.M, a.T + b.T, a.I + b.I, a.Θ + b.Θ⟩
def inv (a : Dim) : Dim := ⟨-a.L, -a.M, -a.T, -a.I, -a.Θ⟩
 
def one : Dim := {}
def meter : Dim := { L := 1 }
def kilogram : Dim := { M := 1 }
def second : Dim := { T := 1 }
def ampere : Dim := { I := 1 }
def kelvin : Dim := { Θ := 1 }
def hertz : Dim := { T := -1 }
def watt : Dim := { M := 1, L := 2, T := -3 }
def joule : Dim := { M := 1, L := 2, T := -2 }
def volt : Dim := { M := 1, L := 2, T := -3, I := -1 }
def ohm : Dim := { M := 1, L := 2, T := -3, I := -2 }
def siemens : Dim := { M := -1, L := -2, T := 3, I := 2 }
 
/-- Ohm's law `V = I·R` is dimensionally consistent. -/
theorem ampere_mul_ohm : ampere.mul ohm = volt := by decide
/-- `P = V·I`. -/
theorem volt_mul_ampere : volt.mul ampere = watt := by decide
/-- `I = G·V` (memristor crossbar). -/
theorem siemens_mul_volt : siemens.mul volt = ampere := by decide
/-- `G = 1/R`. -/
theorem inv_ohm : ohm.inv = siemens := by decide
/-- `E = P·t`. -/
theorem watt_mul_second : watt.mul second = joule := by decide
/-- Heater power `P = V²/R`. -/
theorem volt_sq_div_ohm : (volt.mul volt).mul ohm.inv = watt := by decide
 
end Dim
 
/-- A real-valued physical quantity tagged with its dimension. -/
structure Quantity (d : Dim) where
  val : ℝ
 
namespace Quantity
 
variable {a b : Dim}
 
instance : Add (Quantity a) := ⟨fun x y => ⟨x.val + y.val⟩⟩
instance : Sub (Quantity a) := ⟨fun x y => ⟨x.val - y.val⟩⟩
instance : Neg (Quantity a) := ⟨fun x => ⟨-x.val⟩⟩
instance : HMul (Quantity a) (Quantity b) (Quantity (a.mul b)) := ⟨fun x y => ⟨x.val * y.val⟩⟩
instance : HDiv (Quantity a) (Quantity b) (Quantity (a.mul b.inv)) := ⟨fun x y => ⟨x.val / y.val⟩⟩
instance : SMul ℝ (Quantity a) := ⟨fun c x => ⟨c * x.val⟩⟩
instance : LE (Quantity a) := ⟨fun x y => x.val ≤ y.val⟩
 
@[simp] theorem add_val (x y : Quantity a) : (x + y).val = x.val + y.val := rfl
@[simp] theorem sub_val (x y : Quantity a) : (x - y).val = x.val - y.val := rfl
@[simp] theorem hmul_val (x : Quantity a) (y : Quantity b) : (x * y).val = x.val * y.val := rfl
@[simp] theorem hdiv_val (x : Quantity a) (y : Quantity b) : (x / y).val = x.val / y.val := rfl
 
end Quantity
 
abbrev Volt := Quantity Dim.volt
abbrev Ampere := Quantity Dim.ampere
abbrev Watt := Quantity Dim.watt
abbrev Siemens := Quantity Dim.siemens
abbrev Ohm := Quantity Dim.ohm
abbrev Second := Quantity Dim.second
abbrev Meter := Quantity Dim.meter
abbrev Kelvin := Quantity Dim.kelvin
/-- Angles (radians) and plain numbers are dimensionless. -/
abbrev Radian := Quantity Dim.one
abbrev Scalar := Quantity Dim.one
 
/-- Ohm's law stated on typed quantities: the product of a conductance and a voltage is a current. -/
def ohmsLaw (G : Siemens) (V : Volt) : Ampere := ⟨(G * V).val⟩
 
theorem ohmsLaw_val (G : Siemens) (V : Volt) : (ohmsLaw G V).val = G.val * V.val := rfl
 
end Lumiris