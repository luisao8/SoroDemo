use soroban_sdk::{Address, ConversionError, Env, TryFromVal, Val};

use crate::types::DataKey;

impl TryFromVal<Env, DataKey> for Val {
    type Error = ConversionError;

    fn try_from_val(_env: &Env, v: &DataKey) -> Result<Self, Self::Error> {
        Ok((*v as u32).into())
    }
}

pub fn get_token_a(e: &Env) -> Address {
    e.storage().instance().get(&DataKey::TokenA).unwrap()
}

pub fn get_token_b(e: &Env) -> Address {
    e.storage().instance().get(&DataKey::TokenB).unwrap()
}

pub fn get_token_share(e: &Env) -> Address {
    e.storage().instance().get(&DataKey::TokenShare).unwrap()
}

pub fn get_total_shares(e: &Env) -> i128 {
    e.storage().instance().get(&DataKey::TotalShares).unwrap()
}

pub fn get_reserve_a(e: &Env) -> i128 {
    e.storage().instance().get(&DataKey::ReserveA).unwrap()
}

pub fn get_reserve_b(e: &Env) -> i128 {
    e.storage().instance().get(&DataKey::ReserveB).unwrap()
}

pub fn put_token_a(e: &Env, contract: Address) {
    e.storage().instance().set(&DataKey::TokenA, &contract);
}

pub fn put_token_b(e: &Env, contract: Address) {
    e.storage().instance().set(&DataKey::TokenB, &contract);
}

pub fn put_token_share(e: &Env, contract: Address) {
    e.storage().instance().set(&DataKey::TokenShare, &contract);
}

pub fn put_total_shares(e: &Env, amount: i128) {
    e.storage().instance().set(&DataKey::TotalShares, &amount)
}

pub fn put_reserve_a(e: &Env, amount: i128) {
    e.storage().instance().set(&DataKey::ReserveA, &amount)
}

pub fn put_reserve_b(e: &Env, amount: i128) {
    e.storage().instance().set(&DataKey::ReserveB, &amount)
}