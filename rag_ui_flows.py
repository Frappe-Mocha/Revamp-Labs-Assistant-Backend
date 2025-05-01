import chromadb
from typing import List, Dict, Any
import json
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
    api_key="<Open-ai-key>",
    api_version="2024-02-01",
    azure_endpoint="<endpoint>"
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

# Create (or get) a collection for automation workflows
workflow_collection = client.get_or_create_collection(
    name="automation_workflows",
    embedding_function=embedding_function
)

def add_workflow_document(workflow_doc: Dict[str, Any]):
    """
    Adds a workflow automation document to the RAG database.
    
    Args:
        workflow_doc (Dict): A complete workflow document in the structured format
    """
    # Extract key information for metadata
    workflow_id = workflow_doc.get("workflow_id", "unknown_workflow")
    title = workflow_doc.get("title", "Untitled Workflow")
    application = workflow_doc.get("metadata", {}).get("application", "Unknown Application")
    module = workflow_doc.get("metadata", {}).get("module", "Unknown Module")
    feature = workflow_doc.get("metadata", {}).get("feature", "Unknown Feature")
    
    # Create searchable text for embedding
    # Include title, description, and step descriptions to make it discoverable
    searchable_text = f"{title}. {workflow_doc.get('description', '')}"
    
    # Add step descriptions to make the document more discoverable
    steps = workflow_doc.get("steps", [])
    step_descriptions = [step.get("description", "") for step in steps]
    searchable_text += " " + " ".join(step_descriptions)
    
    # Store the complete document as a JSON string
    full_doc_json = json.dumps(workflow_doc)
    
    # Add to collection
    workflow_collection.add(
        ids=[workflow_id],
        documents=[searchable_text],  # The text that will be embedded and used for semantic search
        metadatas=[{
            "title": title,
            "application": application,
            "module": module,
            "feature": feature,
            "full_document": full_doc_json  # Store the complete document in metadata
        }]
    )

def fetch_relevant_workflow(query: str, n_results: int = 1):
    """
    Fetches relevant workflow documents based on a text description.
    
    Args:
        query (str): Description of the workflow you're looking for
        n_results (int): Number of results to return (default: 1)
        
    Returns:
        List[Dict]: List of complete workflow documents matching the query
    """
    results = workflow_collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["metadatas"]
    )
    
    workflows = []
    metadatas = results.get("metadatas", [])
    
    if metadatas and len(metadatas) > 0:
        for meta in metadatas[0]:  # First query's results
            # Extract and parse the full document from metadata
            if "full_document" in meta:
                workflow = json.loads(meta["full_document"])
                workflows.append(workflow)
    
    return workflows

def get_workflow_count():
    """
    Returns the total number of workflow documents in the RAG database.
    
    Returns:
        int: The number of documents stored in the workflow collection
    """
    # Get collection info which includes count
    collection_info = workflow_collection.count()
    return collection_info

def delete_workflow(workflow_id: str):
    """
    Deletes a workflow document from the RAG database by its workflow_id.
    
    Args:
        workflow_id (str): The unique identifier of the workflow to delete
        
    Returns:
        bool: True if the document was found and deleted, False otherwise
    """
    try:
        # Check if the document exists before deleting
        results = workflow_collection.get(
            ids=[workflow_id],
            include=[]
        )
        
        if results and len(results['ids']) > 0:
            # Document exists, delete it
            workflow_collection.delete(ids=[workflow_id])
            return True
        else:
            # Document not found
            return False
    except Exception as e:
        print(f"Error deleting workflow: {e}")
        return False


if __name__ == "__main__":

    print(get_workflow_count())

    print(fetch_relevant_workflow('create new hubspot company', 1))