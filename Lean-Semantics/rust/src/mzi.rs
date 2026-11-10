//! One calibrated thermo-optic MZI, one live field input, one static signed weight.
//! Float inversion proposes a DAC code; exact interval checks decide acceptance.
use crate::rational::{Interval, Rat};
use crate::{Error, Kind, Op, Program, Result};
use std::collections::BTreeMap;
pub const SCALE: i128 = 1_000_000_000;
#[derive(Clone, Copy, Debug)]
struct Fixed {
    lo: i128,
    hi: i128,
}
fn down(n: i128, d: i128) -> i128 {
    n.div_euclid(d)
}
fn up(n: i128, d: i128) -> i128 {
    -(-n).div_euclid(d)
}
impl Fixed {
    fn of(x: Interval) -> Self {
        Self {
            lo: down(x.lo.n as i128 * SCALE, x.lo.d as i128),
            hi: up(x.hi.n as i128 * SCALE, x.hi.d as i128),
        }
    }
    fn add(self, b: Self) -> Self {
        Self {
            lo: self.lo + b.lo,
            hi: self.hi + b.hi,
        }
    }
    fn neg(self) -> Self {
        Self {
            lo: -self.hi,
            hi: -self.lo,
        }
    }
    fn mul(self, b: Self) -> Self {
        let p = [
            self.lo * b.lo,
            self.lo * b.hi,
            self.hi * b.lo,
            self.hi * b.hi,
        ];
        Self {
            lo: down(*p.iter().min().unwrap(), SCALE),
            hi: up(*p.iter().max().unwrap(), SCALE),
        }
    }
    fn div_int(self, d: i128) -> Self {
        Self {
            lo: down(self.lo, d),
            hi: up(self.hi, d),
        }
    }
}
/// Degree-32 cosine polynomial and absolute Lagrange remainder x^34/34!.
/// Directed integer rounding encloses every polynomial operation.
pub fn cos_enclosure(theta: Interval) -> Result<Interval> {
    let half = "1/2".parse::<Rat>()?;
    let x = theta.mul(Interval::point(half))?;
    if x.mag() > "8".parse()? {
        return Err(Error::new(
            "phase outside certified cosine domain |theta/2| <= 8",
        ));
    }
    let x = Fixed::of(x);
    let square = x.mul(x);
    let mut term = Fixed {
        lo: SCALE,
        hi: SCALE,
    };
    let mut sum = term;
    for j in 1..=16 {
        term = term.mul(square).div_int((2 * j - 1) * (2 * j));
        sum = sum.add(if j % 2 == 0 { term } else { term.neg() });
    }
    let remainder = term.mul(square).div_int(33 * 34);
    let r = remainder.lo.abs().max(remainder.hi.abs());
    Interval::new(
        Rat::new((sum.lo - r).max(-SCALE), SCALE)?,
        Rat::new((sum.hi + r).min(SCALE), SCALE)?,
    )
}
#[derive(Clone, Debug)]
pub struct Device {
    pub id: String,
    pub vmax: Rat,
    pub bits: u32,
    pub k: Rat,
    pub offset: Rat,
    pub phase_error: Rat,
    pub input_limit: Rat,
}
impl Device {
    pub fn parse(text: &str) -> Result<Self> {
        let mut fields = BTreeMap::new();
        let mut header = false;
        for line in text.lines() {
            let t: Vec<_> = line.split('#').next().unwrap().split_whitespace().collect();
            if t.is_empty() {
                continue;
            }
            if !header {
                if t != ["lumiris-mzi", "1"] {
                    return Err(Error::new("expected lumiris-mzi 1 header"));
                }
                header = true;
                continue;
            }
            if t.len() != 2 || fields.insert(t[0], t[1]).is_some() {
                return Err(Error::new("device field duplicated or malformed"));
            }
        }
        let keys = [
            "id",
            "voltage_max",
            "dac_bits",
            "phase_per_v2",
            "phase_offset",
            "phase_error",
            "input_limit",
        ];
        if fields.len() != keys.len() || keys.iter().any(|k| !fields.contains_key(k)) {
            return Err(Error::new("unknown or missing device field"));
        }
        let get = |k: &str| -> Result<Rat> { fields[k].parse() };
        let d = Self {
            id: fields["id"].into(),
            vmax: get("voltage_max")?,
            bits: fields["dac_bits"]
                .parse()
                .map_err(|_| Error::new("invalid DAC bits"))?,
            k: get("phase_per_v2")?,
            offset: get("phase_offset")?,
            phase_error: get("phase_error")?,
            input_limit: get("input_limit")?,
        };
        if d.vmax <= Rat::ZERO
            || d.vmax > "10".parse()?
            || !(2..=16).contains(&d.bits)
            || d.k <= Rat::ZERO
            || d.k > Rat::ONE
            || d.offset.abs() > Rat::ONE
            || !d.phase_error.nonneg()
            || d.phase_error > Rat::ONE
            || d.input_limit <= Rat::ZERO
            || d.input_limit > Rat::ONE
        {
            return Err(Error::new(
                "device parameters outside supported safe domain",
            ));
        }
        Ok(d)
    }
    pub fn voltage(&self, code: u32) -> Result<Rat> {
        if code >= (1 << self.bits) {
            return Err(Error::new("DAC code outside range"));
        }
        self.vmax
            .mul(Rat::new(code as i128, ((1u32 << self.bits) - 1) as i128)?)
    }
    pub fn phase(&self, code: u32) -> Result<Interval> {
        let v = self.voltage(code)?;
        Interval::point(self.k.mul(v.mul(v)?)?.add(self.offset)?).inflate(self.phase_error)
    }
}
#[derive(Debug)]
pub struct Binding {
    pub input: String,
    pub weight: Rat,
    pub local_budget: Rat,
    pub input_range: Interval,
    pub input_error: Rat,
}
pub fn bind(p: &Program) -> Result<Binding> {
    if p.nodes.len() != 3 {
        return Err(Error::new(
            "MZI MVP requires exactly one input, one exact constant, one multiply",
        ));
    }
    let out = p.node(&p.output);
    let (a, b, local) = match &out.kind {
        Kind::Binary {
            op: Op::Mul,
            a,
            b,
            local,
            ..
        } => (p.node(a), p.node(b), *local),
        _ => return Err(Error::new("MZI output must be a multiply")),
    };
    let (input, weight) = match (&a.kind, &b.kind) {
        (Kind::Input, Kind::Const(w)) => (a, (b, *w)),
        (Kind::Const(w), Kind::Input) => (b, (a, *w)),
        _ => {
            return Err(Error::new(
                "MZI multiply needs a static weight and live input",
            ))
        }
    };
    if weight.0.error != Rat::ZERO || weight.1.abs() > Rat::ONE {
        return Err(Error::new("MZI static weight must be exact and in [-1,1]"));
    }
    Ok(Binding {
        input: input.name.clone(),
        weight: weight.1,
        local_budget: local,
        input_range: input.range,
        input_error: input.error,
    })
}
#[derive(Debug)]
pub struct Certificate {
    pub code: u32,
    pub voltage: Rat,
    pub phase: Interval,
    pub transmission: Interval,
    pub weight_error: Rat,
    pub local_error: Rat,
    pub total_error: Rat,
}
impl Certificate {
    pub fn text(&self, d: &Device) -> String {
        format!("lumiris-mzi-certificate 1\nmodel {}\ncode {}\nvoltage {}\nphase {} {}\ntransmission {} {}\nweight_error {}\nlocal_error {}\ntotal_error {}\n",d.id,self.code,self.voltage,self.phase.lo,self.phase.hi,self.transmission.lo,self.transmission.hi,self.weight_error,self.local_error,self.total_error)
    }
}
pub fn compile(p: &Program, d: &Device) -> Result<Certificate> {
    let b = bind(p)?;
    let actual = b.input_range.inflate(b.input_error)?;
    if actual.mag() > d.input_limit {
        return Err(Error::new(
            "MZI input field exceeds calibrated amplitude limit",
        ));
    }
    let theta = 2.0 * b.weight.f64().acos();
    let power = (theta - d.offset.f64()) / d.k.f64();
    let desired = power.max(0.0).sqrt() / d.vmax.f64() * ((1u32 << d.bits) - 1) as f64;
    if !desired.is_finite() {
        return Err(Error::new("inverse model failed"));
    }
    let max = (1u32 << d.bits) - 1;
    let center = desired.round().clamp(0.0, max as f64) as u32;
    let mut best: Option<Certificate> = None;
    for code in center.saturating_sub(1)..=center.saturating_add(1).min(max) {
        let phase = d.phase(code)?;
        let transmission = cos_enclosure(phase)?;
        let weight_error = transmission
            .lo
            .sub(b.weight)?
            .abs()
            .max(transmission.hi.sub(b.weight)?.abs());
        let local_error = weight_error.mul(actual.mag())?;
        let total_error = b.weight.abs().mul(b.input_error)?.add(local_error)?;
        let c = Certificate {
            code,
            voltage: d.voltage(code)?,
            phase,
            transmission,
            weight_error,
            local_error,
            total_error,
        };
        if best.as_ref().is_none_or(|v| c.total_error < v.total_error) {
            best = Some(c);
        }
    }
    let c = best.ok_or_else(|| Error::new("no DAC candidate"))?;
    if c.local_error > b.local_budget || c.total_error > p.tolerance {
        return Err(Error::new(format!(
            "MZI resolution/calibration cannot meet budget: local {}, total {}",
            c.local_error, c.total_error
        )));
    }
    Ok(c)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cosine_bounds() {
        for i in -160..=160 {
            let t = Rat::new(i, 10).unwrap();
            let a = cos_enclosure(Interval::point(t)).unwrap();
            let y = (t.f64() / 2.0).cos();
            assert!(
                a.lo.f64() <= y + 1e-15 && y <= a.hi.f64() + 1e-15,
                "{i}: {a:?}"
            );
        }
    }
    #[test]
    fn broad_cosine() {
        let a = cos_enclosure(Interval::new("-1".parse().unwrap(), "1".parse().unwrap()).unwrap())
            .unwrap();
        assert!(a.lo.f64() <= 0.5f64.cos() && a.hi == Rat::ONE);
    }
}
