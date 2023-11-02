import os
import logging
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
import chainlit as cl
from utils.constants import openai_key, TEMPLATE, INTRODUCTION


logging.info("Starting LLM App")
logging.info(f"Using OpenAI API Key: {openai_key}")

os.environ["OPEN_AI_KEY"] = openai_key

# ==== Set State ====

# Sending an action button within a chatbot message
actions = [
    cl.Action(name="reset_restart", value="example_value", label="Restart/Reset Chat", description="Restart/Reset"),
    cl.Action(name="run_labs", value="example_value", label="Run Diagnostics/Labs", description="Labs"),
    cl.Action(name="score_diagnosis", value="example_value", label="Test Your Diagnosis", description="Diagnosis"),
]

# String description/representation of a medical condition
condition = None

# ==== Define Interaction Functions ====

@cl.action_callback("reset_restart")
async def on_action(action):
    await cl.Message(content=f"Restarting Conversation ....").send()
    
    # RESET STATE
    
    
    # Optionally remove the action button from the chatbot user interface
    # await action.remove()


@cl.on_chat_start
async def main():
    # Create Template
    prompt = PromptTemplate(template=TEMPLATE, input_variables=["condition"])
    # Create Chain
    llm_chain = LLMChain(
        prompt=prompt, 
        llm=OpenAI(temperature=0),
        verbose=True
    )
    
    # Store the chain in the user session
    cl.user_session.set("llm_chain", llm_chain)
    
    # Create Starting Interface/User Directions
    await cl.Message(content=INTRODUCTION).send()
    await cl.Message(content="You can press this button at any time to reset or restart the conversation:", actions=actions).send()
    
    
@cl.on_message
async def main(message: cl.Message):
    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get("llm_chain")  # type: LLMChain

    # Should Check here what STATE we're in - I'm imagining a finite state machine 
    # Select the Chain we want to use based on the STATE we're in. 
    
    # Call the chain asynchronously
    res = await llm_chain.acall(message.content, callbacks=[cl.AsyncLangchainCallbackHandler()])

    # Do any post processing here

    # "res" is a Dict. For this chain, we get the response by reading the "text" key.
    # This varies from chain to chain, you should check which key to read.
    await cl.Message(content=res["text"], actions=actions).send()
    
logging.info("Completed Setup")