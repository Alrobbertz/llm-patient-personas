import os
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
import random
from langchain.prompts.chat import ChatPromptTemplate
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from Prompts import *


class Patient:
    condition = random.choice(['Asthma'])
    gender = random.choice(['Male', 'Female'])

    def __init__(self):
        self.patient_info = self.patient_generator()
        self.physical_exam = self.patient_physical_generator()
        self.diagnostic_exam = self.patient_diagnostic_generator()
        self.treatment_plan = self.treatment_generator()
        self.labs = []

    def patient_generator(self):
        # Instantiate LM
        gpt_3_5_patient = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                     temperature=0.9)
        # Load condition information
        loader = TextLoader(f"drive/MyDrive/LLM/{self.condition}_symptoms_diagnosis.txt")
        disease_context = loader.load()
        # Load relevant text into context
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50, length_function=len,
                                                       is_separator_regex=False)
        disease_documents = text_splitter.split_documents(disease_context)
        disease_documents = [d.page_content for d in disease_documents]
        retriever = Chroma.from_texts(disease_documents, embedding=OpenAIEmbeddings()).as_retriever(
            search_kwargs={"k": 2})
        relevant = retriever.get_relevant_documents(
            f'clinical manifestations or signs and symptoms of {self.condition}')
        # Clean text for passing to LM
        symptoms = [d.page_content for d in relevant]
        symptoms = ' '.join(symptoms)
        # Instantiate and invoke chain
        disease_template = symptoms
        chat_prompt = ChatPromptTemplate.from_messages([("system", patient_template)])
        chain = chat_prompt | gpt_3_5_patient
        patient_output = chain.invoke(
            {'disease_state': self.condition, 'context': disease_template, 'gender': self.gender})
        return patient_output.content

    def patient_physical_generator(self):
        # Instantiate Model
        gpt_3_5_eval = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                  temperature=0.0)
        # Load relevant text into context
        loader = TextLoader(f"drive/MyDrive/LLM/{self.condition}_symptoms_diagnosis.txt")
        disease_context = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50, length_function=len,
                                                       is_separator_regex=False)
        disease_documents = text_splitter.split_documents(disease_context)
        disease_documents = [d.page_content for d in disease_documents]
        retriever = Chroma.from_texts(disease_documents, embedding=OpenAIEmbeddings()).as_retriever(
            search_kwargs={"k": 2})
        relevant = retriever.get_relevant_documents(f'physical exam findings for {self.condition}')
        # Clean text for passing to LM
        physical = [d.page_content for d in relevant]
        physical = ' '.join(physical)
        # Instantiate and invoke chain
        chat_prompt = ChatPromptTemplate.from_messages([("system", physical_template)])
        chain = chat_prompt | gpt_3_5_eval
        patient_eval_out = chain.invoke(
            {'disease_state': self.condition, 'patient_template': self.patient_info, 'context': physical,
             'gender': self.gender})
        return patient_eval_out.content

    def patient_diagnostic_generator(self):
        # Instantiate Model
        gpt_3_5_eval = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                  temperature=0.0)
        # Load relevant text
        loader = TextLoader(f"drive/MyDrive/LLM/{self.condition}_symptoms_diagnosis.txt")
        disease_context = loader.load()
        # Load relevant text into context
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50, length_function=len,
                                                       is_separator_regex=False)
        disease_documents = text_splitter.split_documents(disease_context)
        disease_documents = [d.page_content for d in disease_documents]
        retriever = Chroma.from_texts(disease_documents, embedding=OpenAIEmbeddings()).as_retriever(
            search_kwargs={"k": 2})
        relevant = retriever.get_relevant_documents(
            f'diagnostic exam findings or diagnostic evaluation findings for {self.condition}')
        # Clean text for passing to LM
        diagnostic = [d.page_content for d in relevant]
        diagnostic = ' '.join(diagnostic)
        # Instantiate and invoke chain
        chat_prompt = ChatPromptTemplate.from_messages([("system", diagnostic_template)])
        chain = chat_prompt | gpt_3_5_eval
        patient_eval_out = chain.invoke(
            {'disease_state': self.condition, 'patient_template': self.patient_info, 'context': diagnostic,
             'gender': self.gender})
        return patient_eval_out.content

    def treatment_generator(self):
        # Instantiate LM
        gpt_3_5_treatment = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                       temperature=0.0)
        # Load condition information
        loader = TextLoader(f"drive/MyDrive/LLM/{self.condition}_treatment.txt")
        treatment_context = loader.load()
        # Load relevant text into context
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50, length_function=len,
                                                       is_separator_regex=False)
        treatment_documents = text_splitter.split_documents(treatment_context)
        treatment_documents = [d.page_content for d in treatment_documents]
        retriever = Chroma.from_texts(treatment_documents, embedding=OpenAIEmbeddings()).as_retriever(
            search_kwargs={"k": 3})
        relevant = retriever.get_relevant_documents(f'treatment plan and medications used for {self.condition}')
        # Clean text for passing to LM
        treatment = [d.page_content for d in relevant]
        treatment = ' '.join(treatment)
        # Instantiate and invoke chain
        patient_context = self.patient_info + self.physical_exam + self.diagnostic_exam
        chat_prompt = ChatPromptTemplate.from_messages([("system", treatment_template)])
        chain = chat_prompt | gpt_3_5_treatment
        patient_output = chain.invoke(
            {'disease_state': self.condition, 'context': treatment, 'patient': patient_context, 'gender': self.gender})
        return patient_output.content


class LabGenerator:

    def __init__(self, patient: Patient):
        self.patient = patient
        self.labs_model = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                                     temperature=0.0)
        # Load the document, split by \n, load into retriever
        loader = TextLoader(f"drive/MyDrive/LLM/{patient.gender}_reference_ranges.txt")
        normal_labs = loader.load()
        normal_labs = normal_labs[0].page_content.split('\n')
        self.retriever = Chroma.from_texts(normal_labs,
                                           embedding=OpenAIEmbeddings()).as_retriever(search_kwargs={"k": 1})

    def generate_lab_value(self, lab):
        # Retrieve relevant lab value
        relevant_lab = self.retriever.get_relevant_documents(lab)
        # Instantiate template variables and prompt, create chain and invoke
        chat_prompt = ChatPromptTemplate.from_messages([("system", labs_template)])
        chain = chat_prompt | self.labs_model
        lab_out = chain.invoke({"disease_state":self.patient.condition, "lab":lab,
                                "context":relevant_lab[0].page_content, 'gender':self.patient.gender})
        return lab_out.content
