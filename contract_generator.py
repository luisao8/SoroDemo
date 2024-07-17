from openai import OpenAI
import time
import streamlit as st
import os
import anthropic
import tempfile
import zipfile
import re
import shutil
import requests
import firebase_admin
from firebase_admin import credentials, storage
from io import BytesIO
import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

firebase_creds = dict(st.secrets["firebase"])
with open("firebase_credentials.json", "w") as f:
    json.dump(firebase_creds, f)
cred = credentials.Certificate("firebase_credentials.json")
app = firebase_admin.initialize_app(cred, {'storageBucket':  'sorodemo-80aa6.appspot.com'})
bucket = storage.bucket()


# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client_anthropic = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
problem_statement_assistant_id = st.secrets["PROBLEM_STATEMENT_ASSISTANT_ID"]
liquidity_builder_assistant_id = st.secrets["LIQUIDITY_BUILDER_ASSISTANT_ID"]
token_builder_assistant_id = st.secrets["TOKEN_BUILDER_ASSISTANT_ID"]


def read_contract_template(contract, file):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    contract_path = os.path.join(script_dir, 'contract_files', contract, 'src', file)
    
    with open(contract_path, 'r') as file:
        return file.read()
    
def generate_timestamp():
    # Obtiene el timestamp actual
    now = datetime.datetime.utcnow()
    # Formatea el timestamp como una cadena única
    timestamp = now.strftime("%Y%m%d%H%M%S")
    return timestamp

def generate_temporal_url(zip_file_path):
    # Read the zip file
    with open(zip_file_path, 'rb') as file:
        zip_content = file.read()
    
    # Create a BytesIO object
    bytes_io = BytesIO(zip_content)
    
    # Generate a unique timestamp
    timestamp = generate_timestamp()
    
    # Create a unique blob name
    blob_name = f"smart_contract-{timestamp}.zip"
    
    # Get a reference to the blob
    blob = bucket.blob(blob_name)
    
    # Upload the file
    blob.upload_from_file(bytes_io, content_type='application/zip')
    
    # Generate a signed URL that expires in 1 hour (3600 seconds)
    url_temporal = blob.generate_signed_url(version='v4', expiration=86300, method='GET')
    
    return url_temporal

# Read the contract template

liquidity_contract = read_contract_template("liquidity", "contract.rs")
liquidity_events = read_contract_template("liquidity", "events.rs")
liquidity_interface = read_contract_template("liquidity", "interface.rs")
liquidity_lib = read_contract_template("liquidity", "lib.rs")
liquidity_storage = read_contract_template("liquidity", "storage.rs")
liquidity_test = read_contract_template("liquidity", "test.rs")
liquidity_types = read_contract_template("liquidity", "types.rs")
liquidity_cargo = read_contract_template("liquidity", "cargo.toml")

token_admin = read_contract_template("token", "admin.rs")
token_allowance = read_contract_template("token", "allowance.rs")
token_balance = read_contract_template("token", "balance.rs")
token_contract = read_contract_template("token", "contract.rs")
token_lib = read_contract_template("token", "lib.rs")
token_metadata = read_contract_template("token", "metadata.rs")
token_storage_types = read_contract_template("token", "storage_types.rs")
token_test = read_contract_template("token", "test.rs")
token_cargo = read_contract_template("token", "cargo.toml")

def create_thread():
    thread = client.beta.threads.create()
    return thread.id

def add_message(thread_id, role, content): 
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role=role,
        content=content
    )
    return message

def create_run_and_poll(thread_id, assistant_id):
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id
        
    )
    logger.info(run) 
    i = 0
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        logger.info(f"run {i}")
        i += 1
        if run_status.status == 'completed':
            thread_messages = client.beta.threads.messages.list(thread_id, order="desc")
            message = thread_messages.data[0]  # Access the first message
            content_block = message.content[0]  # Access the first content block
            text = content_block.text  # Access the text object
            value = text.value
            return value
        elif run_status.status == 'failed':
            raise Exception(f"Run failed: {run_status['error']}")
        time.sleep(1)

def generate_documentation(problem_statement, generated_files):
    prompt = f"""You are an expert in Rust and Soroban smart contracts. Your task is to create comprehensive documentation for a liquidity pool smart contract. Here's the context:

Problem Statement:
{problem_statement}

Generated Files:
"""

    for file_name, content in generated_files:
        prompt += f"\n\n{file_name}:\n{content}\n"

    prompt += """
Based on the problem statement and the generated files, please create a detailed markdown (.md) documentation file that includes:

1. An overview of the liquidity pool contract
2. Explanation of key components and their functions
3. How the contract addresses the specific requirements in the problem statement
4. Any notable changes or adaptations made to the original contract template
5. Instructions on how to use and interact with the contract
6. Any potential limitations or considerations for users

Please format the documentation in markdown, using appropriate headers, code blocks, and formatting for readability."""

    response = client_anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4000,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text

def prob_statement(thread_id, problem_statement_assistant_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
# Create a new run with the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=problem_statement_assistant_id
        )
    # Wait for the run to complete
    while run.status != "completed":
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

# Retrieve the assistant's response
    response = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)
    problem_statement = response.data[0].content[0].text.value
    logger.info(problem_statement)
    return problem_statement

def build_liquidity_pool(problem_statement):
    thread_id = create_thread()
    logger.info(f"Thread created: {thread_id}")
    
    liquidity_files = [
        ("contract.rs", liquidity_contract),
        ("events.rs", liquidity_events),
        ("interface.rs", liquidity_interface),
        ("lib.rs", liquidity_lib),
        ("storage.rs", liquidity_storage),
        ("test.rs", liquidity_test),
        ("types.rs", liquidity_types),
        ("cargo.toml", liquidity_cargo)
    ]
    
    responses = []
    
    for file_name, original_code in liquidity_files:
        prompt = f"""This is the problem statement: {problem_statement}
Your role now is to adapt the {file_name} file code for the liquidity pool contract.
Here is the original code:

{original_code}

Please provide the adapted code for {file_name}."""
        
        add_message(thread_id, "user", prompt)
        response = create_run_and_poll(thread_id, liquidity_builder_assistant_id)
        logger.info(response)
        responses.append((file_name, response))
        logger.info(f"Generated {file_name}")
    
    return responses

def build_token_contract(problem_statement, liquidity_pool_documentation):
    thread_id = create_thread()
    logger.info(f"Thread created for token contract: {thread_id}")
    
    # First, add the liquidity pool documentation to the thread
    add_message(thread_id, "user", f"""Here is the documentation for the liquidity pool contract that this token will interact with:

{liquidity_pool_documentation}

Please keep this information in mind when generating the token contract to ensure compatibility and harmony between the two contracts.""")
    
    token_files = [
        ("admin.rs", token_admin),
        ("allowance.rs", token_allowance),
        ("balance.rs", token_balance),
        ("contract.rs", token_contract),
        ("lib.rs", token_lib),
        ("metadata.rs", token_metadata),
        ("storage_types.rs", token_storage_types),
        ("test.rs", token_test),
        ("cargo.toml", token_cargo)
    ]
    
    responses = []
    
    for file_name, original_code in token_files:
        prompt = f"""This is the problem statement: {problem_statement}

Your role now is to adapt the {file_name} file code for the token contract.
Remember to ensure compatibility with the liquidity pool contract as described in the documentation provided earlier.

Here is the original code:

{original_code}

Please provide the adapted code for {file_name}. Include comments explaining any significant changes or adaptations made, especially those ensuring compatibility with the liquidity pool contract."""
        
        add_message(thread_id, "user", prompt)
        response = create_run_and_poll(thread_id, token_builder_assistant_id)
        responses.append((file_name, response))
        logger.info(f"Generated {file_name} for token contract")
    
    
    return responses

def generate_system_overview(problem_statement, liquidity_pool_documentation, token_documentation):
    prompt = f"""As an expert in Soroban smart contracts, your task is to create a concise yet comprehensive overview of a Liquidity Pool and Token contract system. Use the following information:

    Problem Statement:
    {problem_statement}

    Liquidity Pool Contract Documentation:
    {liquidity_pool_documentation}

    Token Contract Documentation:
    {token_documentation}

    Please provide a clear, concise explanation of:
    1. The overall purpose and functionality of the system
    2. How the Liquidity Pool and Token contracts work together
    3. Key features and operations of each contract
    4. Important interaction points between the contracts
    5. Any specific considerations or limitations developers should be aware of

    Your explanation should be informative yet avoid unnecessary verbosity. Aim for a length that a developer can quickly read to get a solid understanding of the system.
    """

    response = client_anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=2000,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text

def extract_rust_code(content):
    code_blocks = re.findall(r'```(rust|toml)\n(.*?)```', content, re.DOTALL)
    if code_blocks:
        return '\n\n'.join(block[1] for block in code_blocks)
    else:
        return content
    
def create_contract_zip(liquidity_responses, token_responses, liquidity_pool_documentation, token_documentation, system_overview):
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = os.path.join(temp_dir, "contracts")
        liquidity_dir = os.path.join(base_dir, "liquidity_pool")
        token_dir = os.path.join(base_dir, "token")
        
        for dir_path in [os.path.join(liquidity_dir, "src"), os.path.join(token_dir, "src")]:
            os.makedirs(dir_path, exist_ok=True)

        def write_files(responses, base_path):
            for file_name, content in responses:
                if file_name in ["cargo.toml", "README.md"]:
                    file_path = os.path.join(base_path, file_name)
                else:
                    file_path = os.path.join(base_path, "src", file_name)
                
                if file_name.endswith('.rs'):
                    content = extract_rust_code(content)
                
                with open(file_path, "w") as f:
                    f.write(content)

        write_files(liquidity_responses, liquidity_dir)
        with open(os.path.join(liquidity_dir, "README.md"), "w") as f:
            f.write(liquidity_pool_documentation)

        write_files(token_responses, token_dir)
        with open(os.path.join(token_dir, "README.md"), "w") as f:
            f.write(token_documentation)

        with open(os.path.join(base_dir, "README.md"), "w") as f:
            f.write(system_overview)

        # Create zip file in a temporary file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        try:
            with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(base_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, base_dir)
                        zipf.write(file_path, arcname)
            
            return temp_zip.name
        except Exception:
            os.unlink(temp_zip.name)
            raise

def send_email_with_make(email, system_overview, temp_url):
    # make.com webhook URL (you'll need to replace this with your actual webhook URL)
    webhook_url = "https://hook.eu2.make.com/9hid97sxq5gfw72ilcftv0w9yh45ioby"

    # Prepare the email content
    email_body = f"""
    <html>
    <body>
    <p>Hi developer,</p>
    <p>Thanks for using our Smart Contract Generator. You can download your smart contract files <a href="{temp_url}">here</a>. This link will expire in 24 hours.</p>
    <p>Here is a comment from the AI system architect about how the smart contract system works so you can have a quick overview:</p>
    <p>{system_overview}</p>
    <p>Best,<br>Missio IA</p>
    </body>
    </html>
    """

    # Prepare the payload for the webhook
    payload = {
        "email": email,
        "subject": "Your Generated Smart Contract",
        "body": email_body
    }

    # Send the POST request to the make.com webhook
    response = requests.post(webhook_url, json=payload)

    # Check if the request was successful
    if response.status_code == 200:
        logger.info("Email sent successfully via make.com")
    else:
        logger.error(f"Failed to send email. Status code: {response.status_code}")



def generate_smart_contract(email, thread_id):
    problem_statement = prob_statement(thread_id, problem_statement_assistant_id)
    liquidity_responses = build_liquidity_pool(problem_statement)
    liquidity_pool_documentation = generate_documentation(problem_statement, liquidity_responses)
    token_responses = build_token_contract(problem_statement, liquidity_pool_documentation)
    token_documentation = generate_documentation(problem_statement, token_responses)
    system_overview = generate_system_overview(problem_statement, liquidity_pool_documentation, token_documentation)
    logger.info(f"SYSTEM OVERVIEW: {system_overview}")
    zip_file_path = create_contract_zip(
        liquidity_responses, 
        token_responses, 
        liquidity_pool_documentation, 
        token_documentation, 
        system_overview
    )
    logger.info("Smart contract generated!")
    temp_url = generate_temporal_url(zip_file_path)
    send_email_with_make(email, system_overview, temp_url)
    os.unlink(zip_file_path)
    return "Smart contract generated and email sent!"

email = "luis.alarcon@missioia.com"
problem_statement = """1. **Tokens**: USDC (USD Coin) and ETH (Ethereum)
2. **Desired Pool Ratio**: 50:50 (equal value of USDC and ETH)
3. **Swap Fees**: 0.3% per transaction
4. **Liquidity Provider Rewards**: Share of the swap fees proportional to their contribution, distributed via LP tokens"""


# generate_smart_contract(email, problem_statement)