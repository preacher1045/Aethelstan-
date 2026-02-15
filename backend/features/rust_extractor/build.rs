fn main() {
    println!("cargo:rustc-link-search=native=C:/Users/dmipr/Downloads/npcap-sdk-1.16/Lib/x64");
    println!("cargo:rustc-link-lib=wpcap");
    println!("cargo:rustc-link-lib=Packet");
}
