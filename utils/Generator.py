import os
import random
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
from langchain.prompts.chat import ChatPromptTemplate
from langchain.prompts import (HumanMessagePromptTemplate,
                               MessagesPlaceholder,
                               PromptTemplate)
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chains import ConversationChain, LLMChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import SystemMessage
import utils
from utils.Prompts import *


class Patient:
    condition = random.choice(['Asthma'])
    gender = random.choice(['Male', 'Female'])
    demeanor = random.choice(['very kind, outgoing, has a tendency to overshare'])

    def __init__(self):
        self.query_dict = {
            'patient_info': f'clinical manifestations or signs and symptoms of {self.condition}',
            'physical': f'physical exam findings for {self.condition}',
            'diagnostic': f'diagnostic exam findings or diagnostic evaluation findings for {self.condition}',
            'treatment': f'treatment plan and medications used for {self.condition}'
        }
        self._patient_info = None
        self._physical_exam = None
        self._diagnostic_exam = None
        self._treatment_plan = None
        self.labs = []
        self.chatbot = None

    async def get_patient_info(self):
        if self._patient_info is None:
            self._patient_info = await self.generator(0.9, patient_template, 'patient_info', 2)
        return self._patient_info

    async def get_physical_exam(self):
        if self._physical_exam is None:
            self._physical_exam = await self.generator(0.0, physical_template, 'physical', 2)
        return self._physical_exam

    async def get_diagnostic_exam(self):
        if self._diagnostic_exam is None:
            self._diagnostic_exam = await self.generator(0.0, diagnostic_template, 'diagnostic', 2)
        return self._diagnostic_exam

    async def get_treatment_plan(self):
        if self._treatment_plan is None:
            self._treatment_plan = await self.generator(0.0, treatment_template, 'treatment', 3)
        return self._treatment_plan

    async def get_chatbot(self):
        if self.chatbot is None and self._patient_info is not None:
            self.chatbot = await self.patient_chat(0.99, persona_template)
        return self.chatbot

    async def generator(self, temperature, template, purpose, k):
        # Instantiate LM
        gpt_3_5 = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                             temperature=temperature)

        # Load condition information
        if purpose != 'treatment':
            loader = TextLoader(
                Path(utils.__file__).parent
                / "data"
                / f"{self.condition}_symptoms_diagnosis.txt", encoding='utf-8'
            )
        else:
            loader = TextLoader(
                Path(utils.__file__).parent
                / "data"
                / f"{self.condition}_treatment.txt", encoding='utf-8'
            )
        context = loader.load()

        # Load relevant text into context and format
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50, length_function=len,
                                                       is_separator_regex=False)
        documents = text_splitter.split_documents(context)
        documents = [d.page_content for d in documents]
        retriever = Chroma.from_texts(documents, embedding=OpenAIEmbeddings()).as_retriever(search_kwargs={"k": k})
        relevant = retriever.get_relevant_documents(self.query_dict[purpose])
        context_doc = [d.page_content for d in relevant]
        context_doc = ' '.join(context_doc)
        # Instantiate and invoke chain for specific purpose
        chain_dict = {'patient_info': {'disease_state': self.condition,
                                       'context': context_doc,
                                       'gender': self.gender},
                      'physical': {'disease_state': self.condition,
                                   'patient_template': self._patient_info if purpose == 'physical' else None,
                                   'context': context_doc,
                                   'gender': self.gender},
                      'diagnostic': {'disease_state': self.condition,
                                     'patient_template': self._patient_info if purpose == 'diagnostic' else None,
                                     'context': context_doc,
                                     'gender': self.gender},
                      'treatment': {'disease_state': self.condition,
                                    'context': context_doc,
                                    'patient': ' '.join(
                                        [str(i) for i in
                                         [self._patient_info, self._physical_exam, self._diagnostic_exam]]) \
                                        if purpose == 'treatment' else None,
                                    'gender': self.gender}}
        chat_prompt = ChatPromptTemplate.from_messages([("system", template)])
        chain = chat_prompt | gpt_3_5
        output = await chain.ainvoke(chain_dict[purpose])
        return output.content

    async def patient_chat(self, temperature, template):
        patient_model = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                   temperature=temperature)
        template = template.format(patient=self._patient_info, demeanor=self.demeanor)
        memory = ConversationSummaryBufferMemory(llm=patient_model, max_token_limit=200, memory_key='chat_summary',
                                                 return_messages=True)
        prompt = ChatPromptTemplate.from_messages([SystemMessage(content=persona_template),
                                                   MessagesPlaceholder(variable_name='chat_summary'),
                                                   HumanMessagePromptTemplate.from_template("{human_input}")])
        llm_chain = LLMChain(llm=patient_model, prompt=prompt, verbose=True, memory=memory)
        return llm_chain


class LabGenerator:

    def __init__(self, patient: Patient):
        self.patient = patient
        self.labs_model = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                     temperature=0.0)

        # Load the document, split by \n, load into retriever
        loader = TextLoader(
            Path(utils.__file__).parent
            / "data"
            / f"{patient.gender}_reference_ranges.txt", encoding='utf-8'
        )
        normal_labs = loader.load()
        normal_labs = normal_labs[0].page_content.split('\n')
        self.retriever = Chroma.from_texts(normal_labs,
                                           embedding=OpenAIEmbeddings()).as_retriever(search_kwargs={"k": 1})

    async def generate_lab_value(self, lab):
        # Retrieve relevant lab value
        relevant_lab = self.retriever.get_relevant_documents(lab)
        # Instantiate template variables and prompt, create chain and invoke
        chat_prompt = ChatPromptTemplate.from_messages([("system", labs_template)])
        chain = chat_prompt | self.labs_model
        lab_out = await chain.ainvoke({"disease_state": self.patient.condition, "lab": lab,
                                       "context": relevant_lab[0].page_content, 'gender': self.patient.gender})
        return lab_out.content


class Diagnosis:

    def __init__(self, patient: Patient):
        self.model = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'])
        self.patient = patient

    async def score_diag(self, user_diagnosis):
        llm_diagnosis = await self.patient.get_diagnostic_exam()
        llm_treatment = await self.patient.get_treatment_plan()

        score_diagnosis_prompt = score_template + "\n User Diagnosis: " + user_diagnosis + "\n Model Diagnosis: " \
                                + llm_diagnosis + '. \n' + llm_treatment
        return self.model.predict(score_diagnosis_prompt)
