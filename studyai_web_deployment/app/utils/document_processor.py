import os
import json
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import HuggingFaceHub
import tempfile

# Initialize embedding model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def process_document(document):
    """
    Process a document and create a vector store for it
    """
    # Create a directory for this document's data if it doesn't exist
    doc_data_dir = os.path.join('app', 'data', str(document.user_id), str(document.id))
    os.makedirs(doc_data_dir, exist_ok=True)
    
    # Load document based on file type
    file_path = document.file_path
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        loader = PyPDFLoader(file_path)
    elif file_extension in ['.txt', '.md']:
        loader = TextLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
    
    documents = loader.load()
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)
    
    # Create vector store
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save vector store
    vectorstore.save_local(doc_data_dir)
    
    return True

def query_document(document, query_text):
    """
    Query the document with a specific question
    """
    # Load the vector store
    doc_data_dir = os.path.join('app', 'data', str(document.user_id), str(document.id))
    vectorstore = FAISS.load_local(doc_data_dir, embeddings)
    
    # Create a retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    # Get relevant documents
    docs = retriever.get_relevant_documents(query_text)
    
    # Use a simpler approach for generating responses
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Use HuggingFace Hub for inference
    llm = HuggingFaceHub(
        repo_id="google/flan-t5-large",
        model_kwargs={"temperature": 0.5, "max_length": 512}
    )
    
    # Create a QA chain
    chain = load_qa_chain(llm, chain_type="stuff")
    
    # Run the chain
    response = chain.run(input_documents=docs, question=query_text)
    
    return response

def generate_flashcards(document):
    """
    Generate flashcards for a document
    """
    # Load the vector store
    doc_data_dir = os.path.join('app', 'data', str(document.user_id), str(document.id))
    vectorstore = FAISS.load_local(doc_data_dir, embeddings)
    
    # Create a retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # Get a sample of documents to create flashcards from
    docs = retriever.get_relevant_documents("important concepts")
    
    # Use HuggingFace Hub for inference
    llm = HuggingFaceHub(
        repo_id="google/flan-t5-large",
        model_kwargs={"temperature": 0.7, "max_length": 1024}
    )
    
    # Create prompt for flashcard generation
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = f"""
    Based on the following text, generate 5 flashcards in JSON format.
    Each flashcard should have a 'front' with a question or term and a 'back' with the answer or definition.
    
    Text:
    {context}
    
    Output only the JSON array with no other text.
    """
    
    # Generate flashcards
    response = llm(prompt)
    
    # Parse the response to extract the JSON
    try:
        # Try to find JSON in the response
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            flashcards = json.loads(json_str)
        else:
            # Fallback: create some basic flashcards
            flashcards = [
                {"front": "What is this document about?", "back": "This document covers " + document.title},
                {"front": "When was this document uploaded?", "back": str(document.uploaded_at)},
                {"front": "Who created this document?", "back": "The document was uploaded by you"},
                {"front": "What is the filename?", "back": document.filename},
                {"front": "What is the purpose of StudyAI?", "back": "To help you study and learn from your documents"}
            ]
    except:
        # Fallback: create some basic flashcards
        flashcards = [
            {"front": "What is this document about?", "back": "This document covers " + document.title},
            {"front": "When was this document uploaded?", "back": str(document.uploaded_at)},
            {"front": "Who created this document?", "back": "The document was uploaded by you"},
            {"front": "What is the filename?", "back": document.filename},
            {"front": "What is the purpose of StudyAI?", "back": "To help you study and learn from your documents"}
        ]
    
    return flashcards

def generate_quiz(document):
    """
    Generate a quiz for a document
    """
    # Load the vector store
    doc_data_dir = os.path.join('app', 'data', str(document.user_id), str(document.id))
    vectorstore = FAISS.load_local(doc_data_dir, embeddings)
    
    # Create a retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # Get a sample of documents to create quiz from
    docs = retriever.get_relevant_documents("important concepts test questions")
    
    # Use HuggingFace Hub for inference
    llm = HuggingFaceHub(
        repo_id="google/flan-t5-large",
        model_kwargs={"temperature": 0.7, "max_length": 1024}
    )
    
    # Create prompt for quiz generation
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = f"""
    Based on the following text, generate 5 multiple-choice questions in JSON format.
    Each question should have a 'question' field, an 'options' array with 4 choices, and a 'correct_answer' field with the index (0-3) of the correct option.
    
    Text:
    {context}
    
    Output only the JSON array with no other text.
    """
    
    # Generate quiz
    response = llm(prompt)
    
    # Parse the response to extract the JSON
    try:
        # Try to find JSON in the response
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            quiz = json.loads(json_str)
        else:
            # Fallback: create a basic quiz
            quiz = [
                {
                    "question": f"What is the title of this document?",
                    "options": [document.title, "Unknown Document", "Study Guide", "Reference Material"],
                    "correct_answer": 0
                },
                {
                    "question": "What tool are you using to study this document?",
                    "options": ["Google Docs", "Microsoft Word", "StudyAI", "Adobe Reader"],
                    "correct_answer": 2
                },
                {
                    "question": "What can you create with StudyAI?",
                    "options": ["Videos", "Flashcards and Quizzes", "Presentations", "Spreadsheets"],
                    "correct_answer": 1
                },
                {
                    "question": "Where is your document stored?",
                    "options": ["On Google Drive", "In your StudyAI account", "On Dropbox", "It's not stored anywhere"],
                    "correct_answer": 1
                },
                {
                    "question": "What format is your document?",
                    "options": [".pdf", ".txt", ".docx", "The actual format of your document"],
                    "correct_answer": 3
                }
            ]
            # Fix the last question to show the actual format
            file_extension = os.path.splitext(document.filename)[1].lower()
            quiz[4]["options"][3] = file_extension
            if file_extension == ".pdf":
                quiz[4]["correct_answer"] = 0
            elif file_extension == ".txt":
                quiz[4]["correct_answer"] = 1
            elif file_extension == ".docx":
                quiz[4]["correct_answer"] = 2
            else:
                quiz[4]["correct_answer"] = 3
    except:
        # Fallback: create a basic quiz
        quiz = [
            {
                "question": f"What is the title of this document?",
                "options": [document.title, "Unknown Document", "Study Guide", "Reference Material"],
                "correct_answer": 0
            },
            {
                "question": "What tool are you using to study this document?",
                "options": ["Google Docs", "Microsoft Word", "StudyAI", "Adobe Reader"],
                "correct_answer": 2
            },
            {
                "question": "What can you create with StudyAI?",
                "options": ["Videos", "Flashcards and Quizzes", "Presentations", "Spreadsheets"],
                "correct_answer": 1
            },
            {
                "question": "Where is your document stored?",
                "options": ["On Google Drive", "In your StudyAI account", "On Dropbox", "It's not stored anywhere"],
                "correct_answer": 1
            },
            {
                "question": "What format is your document?",
                "options": [".pdf", ".txt", ".docx", "The actual format of your document"],
                "correct_answer": 3
            }
        ]
        # Fix the last question to show the actual format
        file_extension = os.path.splitext(document.filename)[1].lower()
        quiz[4]["options"][3] = file_extension
        if file_extension == ".pdf":
            quiz[4]["correct_answer"] = 0
        elif file_extension == ".txt":
            quiz[4]["correct_answer"] = 1
        elif file_extension == ".docx":
            quiz[4]["correct_answer"] = 2
        else:
            quiz[4]["correct_answer"] = 3
    
    return quiz
