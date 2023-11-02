import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

openai_key = os.getenv("OPENAI_API_KEY")

INTRODUCTION = """
Welcome to the Large Language Model (LLM) Patient Simulator! 

This is an interactive interface you can use to practice diagnosing different 
medical conditions. You can 1 ask the LLM Patient Simulator:
1. about their symptoms
2. results of diagnostic tests/labs
3. personal background including medical history and familial history

Try it out now! Ask me something! 
"""

TEMPLATE = """
Pretend you are a medical patient seeking care from a doctor. You will be 
presented with a medical condition. You are tasked to respond with 5 symptoms
that you, as a patient, might have. Please be detailed in describing your 
symptoms.

Medical Condition: {condition}

Let's think step by step.
Symptoms: """