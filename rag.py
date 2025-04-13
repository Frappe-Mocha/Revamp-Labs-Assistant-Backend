import chromadb
from typing import List
import os
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential

import urllib3
import requests

# Disable SSL warnings (optional)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Disable SSL verification globally
requests.packages.urllib3.disable_warnings()
session = requests.Session()
session.verify = False
os.environ["AZURE_CLIENT_DISABLE_SSL_VERIFICATION"] = "1"

# Initialize Azure OpenAI Client
openai_client = AzureOpenAI(
    api_key="6v8fmeXOaPj9XFws1qV1XAYOdkufHhO9725gRuRmVWoFLHOYiHDCJQQJ99BAACHYHv6XJ3w3AAAAACOG6U8D",
    api_version="2024-02-01",
    azure_endpoint="https://anuj-m5gpnbtn-eastus2.openai.azure.com"
)

# ================== Updated Embedding Function ==================
class AzureEmbeddingFunction:
    def __init__(self, client):
        self.client = client

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Embedding function that conforms to Chroma's interface.
        Accepts a list of input texts and returns a list of embeddings.
        """
        embeddings = []
        for text in input:
            response = self.client.embeddings.create(
                input=[text],
                model="text-embedding-3-large"
            )
            embeddings.append(response.data[0].embedding)
        return embeddings

# Initialize the embedding function
embedding_function = AzureEmbeddingFunction(openai_client)

# ================== Chroma Client Initialization ==================
# Create a Chroma client with the new configuration
client = chromadb.PersistentClient(path="db/")  # Use PersistentClient for local storage

# Create (or get) a collection for company profiles
collection = client.get_or_create_collection(
    name="company_profiles",
    embedding_function=embedding_function
)

# ================== Rest of the Code (Unchanged) ==================
def add_document(description_type: str, description: str, company: str):
    """
    Adds a document to the RAG database.
    """
    doc_id = f"{company}_{hash(description)}"
    collection.add(
        ids=[doc_id],
        documents=[description],
        metadatas=[{"description_type": description_type, "company": company}]
    )

# Add documents to the collection
add_document('TAGLINE', '''A complete AI-powered recruiting solution
From candidate sourcing and screening to interview coordination, Apli automates recruiting so you can hire better and faster 
             5x More qualified candidates
10x More efficient recruiters
>200% Return of investment''', 'APLI')

add_document('About', 
             '''
Recruiting Reinvented...
Instead of competing for the minority of applicants on job boards, Apli advertises your job to millions of potential candidates on social media. Our chatbots screen candidates at scale, applying customizable assessments and coordinating interviews - in a single streamlined conversation. And with machine learning, our automatic screening improves with every hire.

Automate screening with AI
Consistently select talent who will perform better and longer based on their similarity with your best employees.

Source more qualified candidates
Engage your candidates from jobs portals and attract additional candidates through social media. Apli targets audiences similar to your best performers with Facebook and Instagram ads, converting up to 200 qualified candidates per day.

Guarantee effective onboarding
Ensure a consistent onboarding journey for every new hire, from welcome videos, trainings, supervisor check-ins to employee satisfaction surveys and exit interviews. Deliver immediate and personalized responses to critical situations in order to prevent employee turnover.

A delightful candidate experience
Show off your employer brand with attractive social media ads, engaging conversational job descriptions and embedded videos. And empower candidates to apply anytime, anywhere with a mobile-friendly application that feels like a chat with an expert human recruiter.

''', 'APLI')

add_document('FEATURES', '''Features
Candidate Chatbot
Intuitive and powerful conversational applications
Candidates are screened by a bot that mimics a structured interview with an expert recruiter. Pre-screening, assessments, interview coordination, document gathering and onboarding happen in one frictionless conversation in a single candidate interface.

Built-in skills assessments and video interviewing
In addition to role-specific filters, customize your screening with psychometric tests, soft and hard skills assessments, video interviews, document checks and more  —  without leaving Apli’s chatbot.

Streamlined interview coordination
Qualified candidates book their own interview at the closest location, selecting from a real-time view of open slots. Apli’s bot follows up with interview preparation tips and interactive maps.
             
Integrate your HR software
Apli seamlessly integrates with the most popular ATS, HRIS and collaboration software including Success Factors, Cornerstone, Workday, Slack and G-Suite. We also support integrations with custom-built HR systems without APIs through Robotic Process Automation.             

''', 'APLI')

def fetch_relevant_documents(query: str, n_results: int = 3):
    """
    Fetches up to n_results relevant documents for the given query.
    Returns a list of strings combining metadata and description.
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas"]
    )
    docs = []
    # The results are lists; we combine the first (and only) query result.
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    if documents and metadatas:
        for doc, meta in zip(documents[0], metadatas[0]):
            docs.append(f"Company: {meta.get('company')}, Type: {meta.get('description_type')}, Info: {doc}")
    return docs