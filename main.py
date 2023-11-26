import os
import logging
import chainlit as cl
from utils.constants import openai_key, INTRODUCTION
from utils.Generator import Patient

logging.info("Starting LLM App")
logging.info(f"Using OpenAI API Key: {openai_key}")

os.environ["OPEN_AI_KEY"] = openai_key

# Sending an action button within a chatbot message
actions = [
    cl.Action(name="reset_restart", value="example_value", label="Restart/Reset Chat", description="Restart/Reset"),
]

# Current Patient Model
PATIENT = None

# =========================================================
#                       CALLBACKS
# =========================================================

@cl.action_callback("reset_restart")
async def on_action(action):
    global PATIENT
    await cl.Message(content=f"Restarting Conversation ....").send()

    # Start new interaction
    PATIENT = Patient()
    await cl.Message(content=f"I'll present a new set of symptoms").send()
    res = await PATIENT.get_patient_info()
    await cl.Message(content=res).send()

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()

# =========================================================
#                  MAIN CHAT FUNCTIONS
# =========================================================

@cl.on_chat_start
async def main():
    global PATIENT
    
    # Create Starting Interface/User Directions
    await cl.Message(content=INTRODUCTION).send()
    await cl.Message(content=f"I'll present a new set of symptoms. This may take a couple minutes, please be patient...").send()

    # Create new Random Condition and Symptoms
    PATIENT = Patient()
    res = await PATIENT.get_patient_info()
    await cl.Message(content=res).send()

    # Add Buttons
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()


@cl.on_message
async def main(message: cl.Message):
    # Get the Agent Chatbot and execute action based on the users input
    chatbot = await PATIENT.get_chatbot()
    res = await chatbot.ainvoke({"input": message.content})
    res = res["output"]
    
    # Do any post processing here
    message = res

    # Send the message response
    await cl.Message(content=message).send()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()


logging.info("Completed Setup")
