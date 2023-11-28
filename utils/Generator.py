import os
import random
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import TextLoader
from langchain.prompts.chat import ChatPromptTemplate
from langchain.prompts import PromptTemplate
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.agents import Tool
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.agents.format_scratchpad import format_log_to_str
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.tools.render import render_text_description
from langchain.agents import AgentExecutor
import utils
from utils.Prompts import *


class Patient:
    condition = random.choice(['Asthma', 'Alcohol_Associated_Liver_Disease', 'COVID', 'Generalized_Anxiety_Disorder',
                               'HFpEF', 'HFrEF', 'Migraine', 'Rheumatoid_Arthritis', 'Type_2_Diabetes'])
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
        
        # Lab Generator
        self.lab_generator = LabGenerator(patient=self)
        
        # Agent Tools
        self.tools = [
            Tool.from_function(
                coroutine=self.lab_generator.generate_lab_value,
                func=None,
                description="I will ALWAYS use the Lab tool when I see the keyword <lab>.",
                name="Lab",
                return_direct=True,
            ),
            Tool.from_function(
                coroutine=self.score_treatment,
                func=None,
                description="I will ALWAYS use the Treatment tool when I see the keyword <treatment>",
                name="Treatment",
                return_direct=True,
            ),
            Tool.from_function(
                coroutine=self.generate_exam,
                func=None,
                description="I will ALWAYS use the Exam tool when I see the keyword <exam>.",
                name="Exam",
                return_direct=True,
            ),
            Tool.from_function(
                coroutine=self.diag_eval,
                func=None,
                description="I will ALWAYS use the Diag tool when I see the keyword <diagnosis>",
                name="Diag",
                return_direct=True,
            ),
        ]

    async def get_patient_info(self, text=None):
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
        if self.chatbot is None:
            if self._patient_info is None:
                _ = await self.get_patient_info()
            self.chatbot = await self.patient_chat(temperature=0.99)
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
        chain_dict = {
            'patient_info': {
                'disease_state': self.condition,
                'context': context_doc,
                'gender': self.gender
            },
            'physical': {
                'disease_state': self.condition,
                'patient_template': self._patient_info if purpose == 'physical' else None,
                'context': context_doc,
                'gender': self.gender
            },
            'diagnostic': {
                'disease_state': self.condition,
                'patient_template': self._patient_info if purpose == 'diagnostic' else None,
                'context': context_doc,
                'gender': self.gender
            },
            'treatment': {
                'disease_state': self.condition,
                'context': context_doc,
                'patient': ' '.join(
                    [str(i) for i in
                        [self._patient_info, self._physical_exam, self._diagnostic_exam]]) \
                    if purpose == 'treatment' else None,
                'gender': self.gender
                }
            }
        
        chat_prompt = ChatPromptTemplate.from_messages([("system", template)])
        chain = chat_prompt | gpt_3_5
        output = await chain.ainvoke(chain_dict[purpose])
        return output.content

    async def patient_chat(self, temperature=1):
        # Create Prompt Template
        prompt = PromptTemplate(
            template = agent_template,
            input_variables=[
                "patient",
                "demeanor",
                "tools",
                "tool_names",
                "chat_history",
                "human_input",
                "agent_scratchpad"
            ]
        )
        
        # Partially Fill-In Members of the Prompt Template
        prompt = prompt.partial(
            patient=await self.get_patient_info(),
            demeanor=self.demeanor,
            tools=render_text_description(self.tools),
            tool_names=", ".join([t.name for t in self.tools]),
        )
        
        # Create Main LLM
        llm = OpenAI(temperature=temperature)
        llm_with_stop = llm.bind(stop=["\nObservation"])
        
        # Create Agent
        agent = (
            {
                "human_input": lambda x: x["input"],
                "agent_scratchpad": lambda x: format_log_to_str(x["intermediate_steps"]),
                "chat_history": lambda x: x["chat_history"],
            }
            | prompt
            | llm_with_stop
            | ReActSingleInputOutputParser()
        )
        
        # Create Executor
        memory = ConversationBufferMemory(memory_key="chat_history")
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            verbose=True, 
            memory=memory, 
            handle_parsing_errors=True
        )
        return agent_executor

    async def generate_exam(self, exam):
        gpt_3_5 = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=os.environ['OPENAI_API_KEY'],
                             temperature=0.0)
        if self._physical_exam is None:
            await self.get_physical_exam()
        if self._diagnostic_exam is None:
            await self.get_diagnostic_exam()
        # Retrieve patient diagnostic/physical exam findings
        patient_exam_findings = self._physical_exam + '\n' + self._diagnostic_exam
        # Instantiate template variables and prompt, create chain and invoke
        chat_prompt = ChatPromptTemplate.from_messages([("system", exam_template)])
        chain = chat_prompt | gpt_3_5
        exam_out = await chain.ainvoke({"disease_state": self.condition, "exam": exam,
                                        "context": patient_exam_findings, 'gender': self.gender})
        return exam_out.content

    async def diag_eval(self, user_diagnosis):
        # Create Model
        model = ChatOpenAI(
            model_name='gpt-3.5-turbo-16k',
            openai_api_key=os.environ['OPENAI_API_KEY'],
            temperature=0.7
        )
        chat_prompt = ChatPromptTemplate.from_messages([("system", diagnosis_eval_template)])
        chain = chat_prompt | model
        score_out = await chain.ainvoke({"model": self.condition,
                                         "user": user_diagnosis})
        return score_out.content

    async def score_treatment(self, user_treatment):
        # Create Model
        model = ChatOpenAI(
            model_name='gpt-3.5-turbo-16k',
            openai_api_key=os.environ['OPENAI_API_KEY'],
            temperature=0.7
        )
        # Fetch Recommended Treatment
        if self._treatment_plan is None:
            await self.get_treatment_plan()

        chat_prompt = ChatPromptTemplate.from_messages([("system", score_template)])
        chain = chat_prompt | model
        score_out = await chain.ainvoke({"model": self._treatment_plan,
                                         "user": user_treatment})
        return score_out.content


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

