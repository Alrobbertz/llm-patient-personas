import os, sys
from os.path import dirname as up

sys.path.append(os.path.abspath(os.path.join(up(__file__), os.pardir)))

openai_key = os.getenv("OPENAI_API_KEY")

INTRODUCTION = """
Welcome to the Large Language Model (LLM) Patient Simulator! 

This is an interactive interface you can use to practice diagnosing different medical conditions.
You can ask the LLM Patient Simulator about their symptoms, for results of diagnostic tests/labs, 
personal background including medical history and familial history, or anything else you might 
see as relevant to ask a patient. 

Once you have reached a potential diagnosis and have created a suggested treatment plan, present 
the simulator with the diagnosis and treatment plan. The simulator will generate a score [0-10] 
based on the quality of your diagnosis and treatment plan and present suggestions for how it might
be improved.

You can use the 'Restart/Reset Chat' button to create a new patient, condition, and set of symptoms 
to diagnose. 
"""