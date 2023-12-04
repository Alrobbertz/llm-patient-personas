import os
import logging
import chainlit as cl
import asyncio
from utils.constants import openai_key, INTRODUCTION
from utils.Generator import Patient

logging.info("Starting LLM App")
logging.info(f"Using OpenAI API Key: {openai_key}")

os.environ["OPEN_AI_KEY"] = openai_key

# Sending an action button within a chatbot message
actions = [
    cl.Action(name="reset_restart", value="example_value", label="Reset Chat", description="Restart/Reset"),
    cl.Action(name="question_answer", value="example_value", label="Agent Chat", description="QA"),
    cl.Action(name="lab_generator", value="example_value", label="Lab Results", description="Labs"),
    cl.Action(name="exam_generator", value="example_value", label="Diagnostic Exam", description="Exam"),
    cl.Action(name="score_diagnosis", value="example_value", label="Test Diagnosis", description="Diagnosis"),
    cl.Action(name="score_treatment", value="example_value", label="Test Treatment Plan", description="Treatment"),
]

# One of {"QA", "LAB", "EXAM", "DIAG", "TREATMENT"}
STATE = "QA"

# Current Patient Model
PATIENT = None

# Define a maximum input length
MAX_INPUT_LENGTH = 5000


# =========================================================
#                       CALLBACKS
# =========================================================

@cl.action_callback("reset_restart")
async def on_action(action):
    global PATIENT
    await cl.Message(content=f"Restarting Conversation ....").send()

    # Start new interaction
    PATIENT = Patient()
    logging.info(f"Patient Condition: {PATIENT.condition}")
    logging.info(f"Patient Demeanor: {PATIENT.demeanor}")
    await cl.Message(content=f"I'll send in the next patient.").send()
    res = await PATIENT.get_patient_info()
    # Hide some Patient Information
    res = res.split("Patient History:")[0]

    # Run calls that aren't immediately needed in background. If tool is called that requires 
    # these before finished, await used in tool function to force completion
    asyncio.create_task(PATIENT.get_diagnostic_exam())
    asyncio.create_task(PATIENT.get_physical_exam())
    asyncio.create_task(PATIENT.get_treatment_plan())

    await cl.Message(content=res).send()

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()


@cl.action_callback("question_answer")
async def on_action(action):
    global STATE

    # SET STATE
    STATE = "QA"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Default Question/Answer Agent").send()


@cl.action_callback("lab_generator")
async def on_action(action):
    global STATE

    # SET STATE
    STATE = "LAB"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Generate Lab Results").send()


@cl.action_callback("exam_generator")
async def on_action(action):
    global STATE

    # SET STATE
    STATE = "EXAM"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Exam Generation").send()


@cl.action_callback("score_diagnosis")
async def on_action(action):
    global STATE

    # SET STATE
    STATE = "DIAG"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Test Your Diagnosis").send()


@cl.action_callback("score_treatment")
async def on_action(action):
    global STATE

    # SET STATE
    STATE = "TREATMENT"
    logging.info(f"Updated State to: {STATE}")
    await cl.Message(content=f"Switching to Test Your Treatment Plan").send()


# =========================================================
#                  MAIN CHAT FUNCTIONS
# =========================================================


@cl.on_chat_start
async def main():
    global PATIENT

    # Create Starting Interface/User Directions
    await cl.Message(content=INTRODUCTION).send()
    await cl.Message(
        content=f"I'll send in the next appointment once they arrive. This may take a couple minutes, please be patient...").send()

    # Create new Random Condition and Symptoms
    PATIENT = Patient()
    logging.info(f"Patient Condition: {PATIENT.condition}")
    logging.info(f"Patient Demeanor: {PATIENT.demeanor}")
    res = await PATIENT.get_patient_info()
    # Hide some Patient Information
    res = res.split("Patient History:")[0]

    # Run calls that aren't immediately needed in background. If tool is called that requires 
    # these before finished, await used in tool function to force completion
    asyncio.create_task(PATIENT.get_diagnostic_exam())
    asyncio.create_task(PATIENT.get_physical_exam())
    asyncio.create_task(PATIENT.get_treatment_plan())

    await cl.Message(content=res).send()

    # Add Buttons
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()


@cl.on_message
async def main(message: cl.Message):
    if len(message.content) > MAX_INPUT_LENGTH:
        res = f"Your input is too long. Please keep it under {MAX_INPUT_LENGTH} characters."
    else:
        # Should Check here what STATE we're in - I'm imagining a finite state machine
        # Select the Chain we want to use based on the STATE we're in.
        match STATE:
            case "QA":
                chatbot = await PATIENT.get_chatbot()
                res = await chatbot.ainvoke({"input": message.content})
                res = res["output"]
            case "LAB":
                res = await PATIENT.lab_generator.generate_lab_value(message.content)
            case "EXAM":
                res = await PATIENT.generate_exam(message.content)
            case "DIAG":
                res = await PATIENT.diag_eval(message.content)
            case "TREATMENT":
                res = await PATIENT.score_treatment(message.content)

    # Send the message response
    await cl.Message(content=res).send()
    await cl.Message(content="Use these buttons to direct the conversation:", actions=actions).send()


logging.info("Completed Setup")
