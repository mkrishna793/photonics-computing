//! Exact bounded rationals. Overflow is an error, never a wrapped certificate.
use crate::{Error, Result};
use std::{cmp::Ordering, fmt, str::FromStr};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Rat {
    pub(crate) n: i64,
    pub(crate) d: i64,
}
fn gcd(mut a: i128, mut b: i128) -> i128 {
    while b != 0 {
        let r = a % b;
        a = b;
        b = r;
    }
    a
}
impl Rat {
    pub const ZERO: Self = Self { n: 0, d: 1 };
    pub const ONE: Self = Self { n: 1, d: 1 };
    pub fn numerator(self) -> i64 {
        self.n
    }
    pub fn denominator(self) -> i64 {
        self.d
    }
    pub fn new(n: i128, d: i128) -> Result<Self> {
        if d == 0 || n == i128::MIN || d == i128::MIN {
            return Err(Error::new("invalid rational"));
        }
        let (n, d) = if d < 0 { (-n, -d) } else { (n, d) };
        let g = gcd(n.abs(), d);
        let (n, d) = (n / g, d / g);
        if n.abs() > i64::MAX as i128 || d > i64::MAX as i128 {
            return Err(Error::new(
                "rational capacity exceeded; simplify or rescale",
            ));
        }
        Ok(Self {
            n: n as i64,
            d: d as i64,
        })
    }
    pub fn add(self, b: Self) -> Result<Self> {
        Self::new(
            self.n as i128 * b.d as i128 + b.n as i128 * self.d as i128,
            self.d as i128 * b.d as i128,
        )
    }
    pub fn neg(self) -> Self {
        Self {
            n: -self.n,
            d: self.d,
        }
    }
    pub fn sub(self, b: Self) -> Result<Self> {
        self.add(b.neg())
    }
    pub fn mul(self, b: Self) -> Result<Self> {
        Self::new(self.n as i128 * b.n as i128, self.d as i128 * b.d as i128)
    }
    pub fn div(self, b: Self) -> Result<Self> {
        Self::new(self.n as i128 * b.d as i128, self.d as i128 * b.n as i128)
    }
    pub fn abs(self) -> Self {
        Self {
            n: self.n.abs(),
            d: self.d,
        }
    }
    pub fn f64(self) -> f64 {
        self.n as f64 / self.d as f64
    }
    pub fn nonneg(self) -> bool {
        self.n >= 0
    }
}
impl Ord for Rat {
    fn cmp(&self, b: &Self) -> Ordering {
        (self.n as i128 * b.d as i128).cmp(&(b.n as i128 * self.d as i128))
    }
}
impl PartialOrd for Rat {
    fn partial_cmp(&self, b: &Self) -> Option<Ordering> {
        Some(self.cmp(b))
    }
}
impl fmt::Display for Rat {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}/{}", self.n, self.d)
    }
}
impl FromStr for Rat {
    type Err = Error;
    fn from_str(s: &str) -> Result<Self> {
        if s.len() > 80 {
            return Err(Error::new("rational token too long"));
        }
        let parts: Vec<_> = s.split('/').collect();
        let parse = |v: &str| {
            v.parse::<i64>()
                .map_err(|_| Error::new("expected integer or n/d rational"))
        };
        match parts.as_slice() {
            [n] => Self::new(parse(n)? as i128, 1),
            [n, d] => Self::new(parse(n)? as i128, parse(d)? as i128),
            _ => Err(Error::new("invalid rational")),
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Interval {
    pub lo: Rat,
    pub hi: Rat,
}
impl Interval {
    pub fn new(lo: Rat, hi: Rat) -> Result<Self> {
        if lo > hi {
            Err(Error::new("reversed interval"))
        } else {
            Ok(Self { lo, hi })
        }
    }
    pub fn point(x: Rat) -> Self {
        Self { lo: x, hi: x }
    }
    pub fn mag(self) -> Rat {
        self.lo.abs().max(self.hi.abs())
    }
    pub fn min_mag(self) -> Rat {
        if self.lo > Rat::ZERO {
            self.lo
        } else if self.hi < Rat::ZERO {
            self.hi.abs()
        } else {
            Rat::ZERO
        }
    }
    pub fn contains(self, b: Self) -> bool {
        self.lo <= b.lo && b.hi <= self.hi
    }
    pub fn inflate(self, e: Rat) -> Result<Self> {
        Self::new(self.lo.sub(e)?, self.hi.add(e)?)
    }
    pub fn add(self, b: Self) -> Result<Self> {
        Self::new(self.lo.add(b.lo)?, self.hi.add(b.hi)?)
    }
    pub fn sub(self, b: Self) -> Result<Self> {
        Self::new(self.lo.sub(b.hi)?, self.hi.sub(b.lo)?)
    }
    pub fn mul(self, b: Self) -> Result<Self> {
        let p = [
            self.lo.mul(b.lo)?,
            self.lo.mul(b.hi)?,
            self.hi.mul(b.lo)?,
            self.hi.mul(b.hi)?,
        ];
        Self::new(*p.iter().min().unwrap(), *p.iter().max().unwrap())
    }
    pub fn div(self, b: Self) -> Result<Self> {
        if b.min_mag() == Rat::ZERO {
            return Err(Error::new("divisor interval touches zero"));
        }
        self.mul(Self::new(Rat::ONE.div(b.hi)?, Rat::ONE.div(b.lo)?)?)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact() {
        let a: Rat = "-2/4".parse().unwrap();
        assert_eq!(a.to_string(), "-1/2");
        assert_eq!(a.add(a).unwrap().to_string(), "-1/1");
    }
    #[test]
    fn reject() {
        for s in ["1/0", "NaN", "1.1", "-9223372036854775808", "1/2/3"] {
            assert!(s.parse::<Rat>().is_err(), "{s}");
        }
    }
    #[test]
    fn overflow() {
        let a: Rat = "9223372036854775807".parse().unwrap();
        assert!(a.add(Rat::ONE).is_err());
        assert_eq!(a.cmp(&a.neg()), Ordering::Greater);
    }
    #[test]
    fn positive_product() {
        let a = Interval::new(Rat::ONE, "2".parse().unwrap()).unwrap();
        let p = a.mul(a).unwrap();
        assert_eq!(p.lo, Rat::ONE);
        assert_eq!(p.hi, "4".parse().unwrap());
        assert!(a.div(p).is_ok());
    }
}
