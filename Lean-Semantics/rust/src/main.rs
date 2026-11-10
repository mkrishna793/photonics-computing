use lumiris::{mzi, Error, Program, Result};
use std::{collections::BTreeMap, fs, path::PathBuf};
fn read(path: &str) -> Result<String> {
    let meta = fs::metadata(path).map_err(|e| Error::new(e.to_string()))?;
    if meta.len() > 65536 {
        return Err(Error::new("input file exceeds 64 KiB"));
    }
    fs::read_to_string(path).map_err(|e| Error::new(e.to_string()))
}
fn run() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("eval") && args.len() >= 2 {
        let p = Program::parse(&read(&args[1])?)?;
        let mut env = BTreeMap::new();
        for arg in &args[2..] {
            let (k, v) = arg
                .split_once('=')
                .ok_or_else(|| Error::new("expected input=value"))?;
            if !matches!(
                p.nodes.iter().find(|n| n.name == k).map(|n| &n.kind),
                Some(lumiris::Kind::Input)
            ) || env.insert(k.into(), v.parse()?).is_some()
            {
                return Err(Error::new("unknown or duplicate input assignment"));
            }
        }
        println!("{}", p.eval(&env)?);
        return Ok(());
    }
    if args.len() != 3 && args.len() != 5 {
        return Err(Error::new("usage: lumiris compile PROGRAM OUTPUT_DIR [--device DEVICE]\n       lumiris eval PROGRAM name=n/d ..."));
    }
    if args[0] != "compile" || (args.len() == 5 && args[3] != "--device") {
        return Err(Error::new("invalid command/options"));
    }
    let source = read(&args[1])?;
    let p = Program::parse(&source)?;
    let physical = if args.len() == 5 {
        let text = read(&args[4])?;
        let device = mzi::Device::parse(&text)?;
        let c = mzi::compile(&p, &device)?;
        Some((text, c.text(&device)))
    } else {
        None
    };
    let out = PathBuf::from(&args[2]);
    if out.exists() {
        return Err(Error::new(
            "output directory already exists; choose a fresh path",
        ));
    }
    fs::create_dir_all(&out).map_err(|e| Error::new(e.to_string()))?;
    let write = |name: &str, text: &str| {
        fs::write(out.join(name), text).map_err(|e| Error::new(e.to_string()))
    };
    write("program.lumi", &source)?;
    write("arithmetic.cert", &p.certificate())?;
    if let Some((device, certificate)) = physical {
        write("device.mzi", &device)?;
        write("physical.cert", &certificate)?;
    }
    println!(
        "Compiled {} nodes. Output {}: range [{}, {}], error <= {} (requested {}).",
        p.nodes.len(),
        p.output,
        p.node(&p.output).range.lo,
        p.node(&p.output).range.hi,
        p.node(&p.output).error,
        p.tolerance
    );
    println!("Artifacts: {}. Run scripts/check_certificate.py to independently check them; compilation alone is not verification.",out.display());
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("lumiris: {e}");
        std::process::exit(1);
    }
}
