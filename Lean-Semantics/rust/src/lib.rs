//! Lumiris v1: bounded straight-line arithmetic, explicit contracts, fail-closed analysis.
pub mod mzi;
pub mod rational;
use rational::{Interval, Rat};
use std::{collections::BTreeMap, fmt};
#[derive(Clone, Debug)]
pub struct Error(String);
impl Error {
    pub fn new(s: impl Into<String>) -> Self {
        Self(s.into())
    }
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}
impl std::error::Error for Error {}
pub type Result<T> = std::result::Result<T, Error>;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Op {
    Add,
    Sub,
    Mul,
    Div,
}
impl Op {
    pub fn name(self) -> &'static str {
        match self {
            Self::Add => "add",
            Self::Sub => "sub",
            Self::Mul => "mul",
            Self::Div => "div",
        }
    }
}
#[derive(Clone, Debug)]
pub enum Kind {
    Input,
    Const(Rat),
    Binary {
        op: Op,
        a: String,
        b: String,
        local: Rat,
        input: Interval,
        output: Interval,
    },
}
#[derive(Clone, Debug)]
pub struct Node {
    pub name: String,
    pub kind: Kind,
    pub range: Interval,
    pub error: Rat,
}
#[derive(Clone, Debug)]
pub struct Program {
    pub nodes: Vec<Node>,
    pub output: String,
    pub tolerance: Rat,
}
fn rat(s: &str) -> Result<Rat> {
    s.parse()
}
fn nonneg(x: Rat) -> Result<Rat> {
    if x.nonneg() {
        Ok(x)
    } else {
        Err(Error::new("negative error/tolerance"))
    }
}
fn identifier(s: &str) -> bool {
    s.len() <= 64
        && s.as_bytes()
            .first()
            .is_some_and(|c| c.is_ascii_alphabetic())
        && s.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_')
}
impl Program {
    pub fn parse(source: &str) -> Result<Self> {
        if source.len() > 65536 {
            return Err(Error::new("program exceeds 64 KiB"));
        }
        let mut nodes: Vec<Node> = Vec::new();
        let mut names = BTreeMap::<String, usize>::new();
        let mut output = None;
        let mut header = false;
        for (line_no, line) in source.lines().enumerate() {
            let t: Vec<_> = line.split('#').next().unwrap().split_whitespace().collect();
            if t.is_empty() {
                continue;
            }
            let result = (|| -> Result<()> {
                if !header {
                    if t != ["lumiris", "1"] {
                        return Err(Error::new("expected lumiris 1 header"));
                    }
                    header = true;
                    return Ok(());
                }
                if output.is_some() {
                    return Err(Error::new("output must be the final statement"));
                }
                if t[0] == "output" {
                    if t.len() != 3 || !names.contains_key(t[1]) {
                        return Err(Error::new("output requires an existing node and tolerance"));
                    }
                    let tolerance = nonneg(rat(t[2])?)?;
                    if nodes[*names.get(t[1]).unwrap()].error > tolerance {
                        return Err(Error::new(
                            "output error budget exceeds requested tolerance",
                        ));
                    }
                    output = Some((t[1].to_string(), tolerance));
                    return Ok(());
                }
                if nodes.len() >= 256 {
                    return Err(Error::new("at most 256 nodes supported"));
                }
                if t.len() < 2 || !identifier(t[1]) || names.contains_key(t[1]) {
                    return Err(Error::new("invalid or duplicate node name"));
                }
                let node = match t[0] {
                    "input" if t.len() == 5 => Node {
                        name: t[1].into(),
                        kind: Kind::Input,
                        range: Interval::new(rat(t[2])?, rat(t[3])?)?,
                        error: nonneg(rat(t[4])?)?,
                    },
                    "const" if t.len() == 4 => {
                        let v = rat(t[2])?;
                        Node {
                            name: t[1].into(),
                            kind: Kind::Const(v),
                            range: Interval::point(v),
                            error: nonneg(rat(t[3])?)?,
                        }
                    }
                    "add" | "sub" | "mul" | "div" if t.len() == 9 => {
                        let op = match t[0] {
                            "add" => Op::Add,
                            "sub" => Op::Sub,
                            "mul" => Op::Mul,
                            _ => Op::Div,
                        };
                        let get = |s: &str| -> Result<&Node> {
                            names.get(s).map(|i| &nodes[*i]).ok_or_else(|| {
                                Error::new(format!("undefined or forward reference: {s}"))
                            })
                        };
                        let (a, b) = (get(t[2])?, get(t[3])?);
                        let local = nonneg(rat(t[4])?)?;
                        let input = Interval::new(rat(t[5])?, rat(t[6])?)?;
                        let physical_output = Interval::new(rat(t[7])?, rat(t[8])?)?;
                        if !input.contains(a.range.inflate(a.error)?)
                            || !input.contains(b.range.inflate(b.error)?)
                        {
                            return Err(Error::new(
                                "perturbed operand outside device input domain",
                            ));
                        }
                        let range = match op {
                            Op::Add => a.range.add(b.range)?,
                            Op::Sub => a.range.sub(b.range)?,
                            Op::Mul => a.range.mul(b.range)?,
                            Op::Div => a.range.div(b.range)?,
                        };
                        let ea = a.error;
                        let eb = b.error;
                        let ma = a.range.mag();
                        let mb = b.range.mag();
                        let propagated = match op {
                            Op::Add | Op::Sub => ea.add(eb)?,
                            Op::Mul => ea.mul(mb)?.add(ma.mul(eb)?)?.add(ea.mul(eb)?)?,
                            Op::Div => {
                                let m = b.range.min_mag();
                                if eb >= m {
                                    return Err(Error::new("perturbed divisor can reach zero"));
                                }
                                ea.mul(mb)?.add(ma.mul(eb)?)?.div(m.mul(m.sub(eb)?)?)?
                            }
                        };
                        let error = propagated.add(local)?;
                        if !physical_output.contains(range.inflate(error)?) {
                            return Err(Error::new(
                                "perturbed result outside device output domain (saturation)",
                            ));
                        }
                        Node {
                            name: t[1].into(),
                            kind: Kind::Binary {
                                op,
                                a: t[2].into(),
                                b: t[3].into(),
                                local,
                                input,
                                output: physical_output,
                            },
                            range,
                            error,
                        }
                    }
                    _ => return Err(Error::new("unknown statement or wrong number of fields")),
                };
                names.insert(node.name.clone(), nodes.len());
                nodes.push(node);
                Ok(())
            })();
            result.map_err(|e| Error::new(format!("line {}: {e}", line_no + 1)))?;
        }
        let (output, tolerance) = output.ok_or_else(|| Error::new("missing output statement"))?;
        Ok(Self {
            nodes,
            output,
            tolerance,
        })
    }
    pub fn node(&self, name: &str) -> &Node {
        self.nodes
            .iter()
            .find(|n| n.name == name)
            .expect("validated reference")
    }
    /// Exact rational reference interpretation. Input uncertainty belongs to analysis, not eval.
    pub fn eval(&self, env: &BTreeMap<String, Rat>) -> Result<Rat> {
        let mut values = BTreeMap::new();
        for n in &self.nodes {
            let v = match &n.kind {
                Kind::Input => {
                    let v = *env
                        .get(&n.name)
                        .ok_or_else(|| Error::new(format!("missing input {}", n.name)))?;
                    if !n.range.contains(Interval::point(v)) {
                        return Err(Error::new("input outside declared range"));
                    }
                    v
                }
                Kind::Const(c) => *c,
                Kind::Binary { op, a, b, .. } => {
                    let x: Rat = values[a];
                    let y: Rat = values[b];
                    match op {
                        Op::Add => x.add(y)?,
                        Op::Sub => x.sub(y)?,
                        Op::Mul => x.mul(y)?,
                        Op::Div => x.div(y)?,
                    }
                }
            };
            values.insert(n.name.clone(), v);
        }
        Ok(values[&self.output])
    }
    pub fn certificate(&self) -> String {
        let mut s = String::from("lumiris-certificate 1\n");
        for n in &self.nodes {
            s.push_str(&format!(
                "node {} {} {} {}\n",
                n.name, n.range.lo, n.range.hi, n.error
            ));
        }
        s.push_str(&format!("output {} {}\n", self.output, self.tolerance));
        s
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unsafe_division() {
        assert!(Program::parse(
            "lumiris 1\ninput x -1 1 0\nconst a 1 0\ndiv y a x 0 -2 2 -10 10\noutput y 1"
        )
        .is_err());
    }
    #[test]
    fn uncertain_division() {
        assert!(Program::parse(
            "lumiris 1\ninput x 1 2 1\nconst a 1 0\ndiv y a x 0 -3 3 -10 10\noutput y 10"
        )
        .is_err());
    }
    #[test]
    fn actual_domain() {
        assert!(Program::parse(
            "lumiris 1\ninput x 0 1 1/10\nconst a 1 0\nmul y a x 0 0 1 -2 2\noutput y 1"
        )
        .is_err());
    }
    #[test]
    fn constant_error() {
        let p = Program::parse(
            "lumiris 1\nconst a 1 1/10\nconst b 2 1/10\nmul y a b 1/100 -3 3 -4 4\noutput y 1",
        )
        .unwrap();
        assert_eq!(p.node("y").error, "8/25".parse().unwrap());
    }
    #[test]
    fn rejects_bad_syntax() {
        for s in [
            "",
            "lumiris 2",
            "lumiris 1\nconst a 0 0\nconst a 1 0\noutput a 0",
            "lumiris 1\nadd a b c 0 -1 1 -2 2\noutput a 0",
            "lumiris 1\nconst a 1 -1\noutput a 0",
        ] {
            assert!(Program::parse(s).is_err());
        }
    }
    #[test]
    fn exact_division() {
        let p=Program::parse("lumiris 1\ninput x 1 2 0\nmul square x x 0 0 4 0 4\nconst one 1 0\ndiv y one square 0 0 4 0 2\noutput y 0").unwrap();
        assert_eq!(p.node("y").range.lo, "1/4".parse().unwrap());
        let mut e = BTreeMap::new();
        e.insert("x".into(), "2".parse().unwrap());
        assert_eq!(p.eval(&e).unwrap(), "1/4".parse().unwrap());
    }
}
