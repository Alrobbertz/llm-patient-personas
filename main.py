import os
import logging
from langchain import PromptTemplate, LLMChain
from langchain.llms import OpenAI
import chainlit as cl
from utils.constants import openai_key, TEMPLATE


logging.info("Starting LLM App")
logging.info(openai_key)

os.environ["OPEN_AI_KEY"] = openai_key



@cl.on_chat_start
def main():
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
    
    
@cl.on_message
async def main(message: cl.Message):
    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get("llm_chain")  # type: LLMChain

    # Call the chain asynchronously
    res = await llm_chain.acall(message.content, callbacks=[cl.AsyncLangchainCallbackHandler()])

    # Do any post processing here

    # "res" is a Dict. For this chain, we get the response by reading the "text" key.
    # This varies from chain to chain, you should check which key to read.
    await cl.Message(content=res["text"]).send()
    
logging.info("Completed Setup")