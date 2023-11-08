import os
import logging
import chainlit as cl
from utils.constants import openai_key, INTRODUCTION
from utils.Generator import Patient, LabGenerator

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

# Current Patient Model
PATIENT = None
LAB_GEN = None

# =========================================================
#                       CALLBACKS 
# =========================================================

@cl.action_callback("reset_restart")
async def on_action(action):
    global STATE
    await cl.Message(content=f"Restarting Conversation ....").send()
    
    # Start new interaction
    PATIENT = Patient()
    await cl.Message(content=f"I'll present a new set of symptoms").send()
    res =  await PATIENT.get_patient_info()
    await cl.Message(content=res).send()
    
    # RESET STATE
    STATE = "QA"

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
    global PATIENT
    global LAB_GEN
   
    await cl.Message(content="Setting Up Patient Backend...").send()
    PATIENT = Patient()
    res =  await PATIENT.get_patient_info()
    LAB_GEN = LabGenerator(patient=PATIENT)
   
    # Create Starting Interface/User Directions
    await cl.Message(content=INTRODUCTION).send()
    
    # Create new Random Condition and Symptoms
    await cl.Message(content=f"I'll present a new set of symptoms").send()
    await cl.Message(content=res).send()
    
    # Add Buttons
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()
    
    
@cl.on_message
async def main(message: cl.Message):
    # Should Check here what STATE we're in - I'm imagining a finite state machine 
    # Select the Chain we want to use based on the STATE we're in. 
    logging.info(f"Selecting Chain for STATE: {STATE}")
    match STATE:
        case "QA":
            # Just for Demo TODO: Remove once Chains are implemented
            res = f"QA Chain Not Implemented"
        case "LAB":
            res = LAB_GEN.generate_lab_value(message.content)
        case "DIAG":
            # Just for Demo TODO: Remove once Chains are implemented
            res = f"Diagnostic Chain Not Implemented"      

    # Do any post processing here
    message = res

    # Send the message response
    await cl.Message(content=message).send()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()
    

logging.info("Completed Setup")
