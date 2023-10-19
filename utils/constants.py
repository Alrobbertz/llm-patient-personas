import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

from utils.helper import *

openai_key = os.getenv("OPENAI_API_KEY")

TEMPLATE = """
Pretend you are a medical patient seeking care from a doctor. You will be 
presented with a medical condition. You are tasked to respond with 5 symptoms
that you, as a patient, might have. Please be detailed in describing your 
symptoms.

Medical Condition: {condition}

Let's think step by step.
Symptoms: """