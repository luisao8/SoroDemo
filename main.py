import streamlit as st
from openai import OpenAI
import time
from contract_generator import generate_smart_contract

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "assistant" not in st.session_state:
    st.session_state.assistant = client.beta.assistants.retrieve(st.secrets["QUESTION_ASSISTANT_ID"])

if "thread" not in st.session_state:
    st.session_state.thread = client.beta.threads.create()

if "email" not in st.session_state:
    st.session_state.email = ""

if "generation_in_progress" not in st.session_state:
    st.session_state.generation_in_progress = False

# Set up the Streamlit page
st.set_page_config(page_title="Smart Contract Generator Assistant", layout="wide")

# Add custom CSS to set dark theme and style inputs
st.markdown("""
    <style>
    .stApp {
        background-color: #1E1E1E;
        color: white;
    }
    .stTextInput > div > div > input {
        background-color: #2D2D2D;
        color: white;
    }
    .stChatInput {
        background-color: #2D2D2D;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Title
st.title("Smart Contract Generator Assistant")

# Email input
email = st.text_input("Enter your email address:", key="email_input")
if email != st.session_state.email:
    st.session_state.email = email

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Single chat input at the bottom
if not st.session_state.generation_in_progress:
    user_input = st.chat_input("Hi! I'm here to help you generate a Smart Contract", key="chat_input")
    if user_input:
        # Process user input and generate response
        # For now, we'll just echo the input
    

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Add the user's message to the thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread.id,
            role="user",
            content=user_input
        )

        # Create a run
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread.id,
            assistant_id=st.session_state.assistant.id
        )

        # Wait for the run to complete or require action
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread.id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                break
            elif run_status.status == 'requires_action':
                for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                    if tool_call.function.name == "generate_contract":
                        # Check if email is provided
                        if not st.session_state.email:
                            st.error("Please enter your email address before generating the contract.")
                            client.beta.threads.runs.cancel(
                                thread_id=st.session_state.thread.id,
                                run_id=run.id
                            )
                            break

                        # Stop the conversation and start contract generation
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Smart contract generation has started. You will receive the contract at {st.session_state.email} once it's ready. Please wait..."
                        })
                        with st.chat_message("assistant"):
                            st.markdown(f"Smart contract generation has started. You will receive the contract at {st.session_state.email} once it's ready. Please wait...")
                        
                        # Disable messaging
                        st.session_state.generation_in_progress = True
                        
                        # Manually end the run
                        client.beta.threads.runs.cancel(
                            thread_id=st.session_state.thread.id,
                            run_id=run.id
                        )
                        
                        # Call the smart contract generation function
                        zip_file_path = generate_smart_contract(st.session_state.email, st.session_state.thread.id)
                        
                        # Here you would trigger the make.com workflow to send the email
                        # For example:
                        # trigger_make_workflow(zip_file_path, st.session_state.email)
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Smart contract has been generated and will be sent to {st.session_state.email} shortly."
                        })
                        with st.chat_message("assistant"):
                            st.markdown(f"Smart contract has been generated and will be sent to {st.session_state.email} shortly.")
                        
                        # Re-enable messaging
                        st.session_state.generation_in_progress = False
                        
                        break  # Exit the for loop

            if st.session_state.generation_in_progress:
                break  # Exit the while loop if contract generation started
            time.sleep(1)

        # Retrieve and display only the latest assistant message
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread.id,
            order="desc",
            limit=1
        )

        for message in messages.data:
            if message.role == "assistant" and message.content[0].type == "text":
                assistant_response = message.content[0].text.value
                if not st.session_state.messages or st.session_state.messages[-1]["role"] != "assistant":
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                    with st.chat_message("assistant"):
                        st.markdown(assistant_response)
