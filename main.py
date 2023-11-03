import os
import logging
import random
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
import chainlit as cl
from utils.constants import openai_key, SYMPTOMS_TEMPLATE, INTRODUCTION


logging.info("Starting LLM App")
logging.info(f"Using OpenAI API Key: {openai_key}")

os.environ["OPEN_AI_KEY"] = openai_key

# ==== Set State ====

# Sending an action button within a chatbot message
actions = [
    cl.Action(name="reset_restart", value="example_value", label="Restart/Reset Chat", description="Restart/Reset"),
    cl.Action(name="question_answer", value="example_value", label="Generic Question/Answer", description="QA"),
    cl.Action(name="run_labs", value="example_value", label="Run Diagnostics/Labs", description="Labs"),
    cl.Action(name="score_diagnosis", value="example_value", label="Test Your Diagnosis", description="Diagnosis"),
]

# One of {"QA", "LAB", "DIAG"}
STATE = "QA"

# String description/representation of a medical condition
CONDITION = None

# =========================================================
#                       CALLBACKS 
# =========================================================

@cl.action_callback("reset_restart")
async def on_action(action):
    global STATE
    await cl.Message(content=f"Restarting Conversation ....").send()
    
    # RESET STATE
    STATE = "QA"
    
    # Start new interaction
    await reset_restart()

    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Generic Question/Answer").send()
    # Optionally remove the action button from the chatbot user interface
    # await action.remove()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()
    
@cl.action_callback("question_answer")
async def on_action(action):
    global STATE
    
    # SET STATE
    STATE = "QA"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Generic Question/Answer").send()

@cl.action_callback("run_labs")
async def on_action(action):
    global STATE
    
    # SET STATE
    STATE = "LAB"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Run Diagnostics/Lab").send()

@cl.action_callback("score_diagnosis")
async def on_action(action):
    global STATE
    
    # SET STATE
    STATE = "DIAG"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Test Your Diagnosis").send()

# =========================================================
#                  MAIN CHAT FUNCTIONS  
# =========================================================

@cl.on_chat_start
async def main():
    # Create Templates
    symptoms_prompt = PromptTemplate(template=SYMPTOMS_TEMPLATE, input_variables=["condition"])
    # qa_template = PromptTemplate()        # Generic Question/Answer? 
    # lab_template = PromptTemplate()       # Running Diagnostic/ Lab Tests? 
    # diag_template = PromptTemplate()      # Evaluating Final Diagnosis? 
    
    # Create Chains
    symptoms_chain = LLMChain(
        prompt=symptoms_prompt, 
        llm=OpenAI(temperature=0),
        verbose=True
    )
    # qa_chain = LLMChain()
    # lab_chain = LLMChain()
    # diag_chain = LLMChain()
    
    # Store the chain in the user session
    cl.user_session.set("symptoms_chain", symptoms_chain)
    # cl.user_session.set("qa_chain", qa_chain)
    # cl.user_session.set("lab_chain", lab_chain)
    # cl.user_session.set("diag_chain", diag_chain)
    
    # Create Starting Interface/User Directions
    await cl.Message(content=INTRODUCTION).send()
    
    # Create new Random Condition and Symptoms
    await reset_restart()
    
    # Add Buttons
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()
    
    
@cl.on_message
async def main(message: cl.Message):
    # Should Check here what STATE we're in - I'm imagining a finite state machine 
    # Select the Chain we want to use based on the STATE we're in. 
    logging.info(f"Selecting Chain for STATE: {SYMPTOMS_TEMPLATE}")
    match STATE:
        case "QA":
            state_chain = "qa_chain"
        case "LAB":
            state_chain = "lab_chain"
        case "DIAG":
            state_chain = "diag_chain"            

    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get(state_chain)  # type: LLMChain
    
    # Call the chain asynchronously # TODO - Uncomment once Chains are implemented
    # res = await llm_chain.acall(
    #     message.content, 
    #     callbacks=[cl.AsyncLangchainCallbackHandler()]
    # )
    
    # Just for Demo TODO: Remove once Chains are implemented
    res = {
        "text": f"Chain {state_chain} Not Implemented"
    }

    # Do any post processing here
    # "res" is a Dict. For this chain, we get the response by reading the "text" key.
    # This varies from chain to chain, you should check which key to read.
    message = res["text"]

    # Send the message response
    await cl.Message(content=message).send()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()
    

# =========================================================
#                       HELPERS
# =========================================================

def get_random_condition():
    condition = random.sample(["Asthma", "Flu", ""], 1)[0]
    logging.info(f"Selected Random Condition: {condition}")
    return condition
    
async def reset_restart():
    global CONDITION
    await cl.Message(content=f"I'll present a new set of symptoms").send()
    CONDITION = get_random_condition()
    symptoms_chain = cl.user_session.get("symptoms_chain")
    res = await symptoms_chain.acall(CONDITION, callbacks=[cl.AsyncLangchainCallbackHandler()])
    await cl.Message(content=res["text"]).send()
    
logging.info("Completed Setup")