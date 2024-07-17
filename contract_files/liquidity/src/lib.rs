#![no_std]

mod contract;
mod event;
mod interface;
mod storage;
mod types;

#[cfg(test)]
mod test;

pub mod token {
    soroban_sdk::contractimport!(
        file = "../../target/wasm32-unknown-unknown/release/soroban_token_contract.optimized.wasm"
    );
}