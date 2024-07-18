# Smart Contract Generator

This project is a Python-based tool that generates customized Soroban smart contracts for liquidity pools and tokens using OpenAI's GPT models and Anthropic's Claude model.

## Features

- Generates problem statements for smart contract requirements
- Creates customized liquidity pool and token contracts based on templates
- Produces comprehensive documentation for each contract
- Generates a system overview explaining how the contracts work together
- Packages all generated files into a zip archive
- Sends an email to the user with a download link and system overview

## Key Components

1. **OpenAI Integration**: Uses OpenAI's API for generating contract code and documentation.
2. **Anthropic Integration**: Uses Claude model for additional documentation generation.
3. **Firebase Storage**: Stores generated zip files and creates temporary download URLs.
4. **Email Notification**: Sends emails with download links using a Make.com (Integromat) webhook.

## Main Functions

- `prob_statement()`: Generates a problem statement for the smart contract.
- `build_liquidity_pool()`: Creates customized liquidity pool contract files.
- `build_token_contract()`: Creates customized token contract files.
- `generate_documentation()`: Produces detailed documentation for each contract.
- `generate_system_overview()`: Creates a comprehensive overview of both contracts.
- `create_contract_zip()`: Packages all generated files into a zip archive.
- `generate_smart_contract()`: Orchestrates the entire contract generation process.

## Usage

The main entry point is the `generate_smart_contract(email, thread_id)` function, which takes an email address and a thread ID as input. It generates the smart contracts, documentation, and sends an email to the user with the download link.

## Dependencies

- OpenAI
- Anthropic
- Streamlit
- Firebase Admin
- Requests

## Note

This script requires various API keys and secrets to be set up in the Streamlit secrets manager for OpenAI, Anthropic, and Firebase integration.
