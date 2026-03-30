use anyhow::Result;
use shared::scaffold_banner;

#[tokio::main]
async fn main() -> Result<()> {
    println!("{}", scaffold_banner("ws-gateway"));
    Ok(())
}
