import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

openai_key = os.getenv("OPENAI_API_KEY")

INTRODUCTION = """
Welcome to the Large Language Model (LLM) Patient Simulator! 

This is an interactive interface you can use to practice diagnosing different 
medical conditions. You can ask the LLM Patient Simulator:
1. about their symptoms
2. results of diagnostic tests/labs
3. personal background including medical history and familial history (Generic Q/A)

Use the buttons below to direct the flow of your conversation! 
"""