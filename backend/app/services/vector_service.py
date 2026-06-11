import os
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize database and model at module level
try:
    _persist_dir = "./vector_store"
    os.makedirs(_persist_dir, exist_ok=True)
    
    _chroma_client = chromadb.PersistentClient(path=_persist_dir)
    _collection = _chroma_client.get_or_create_collection(name="study_materials")
    
    _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Warning: Failed to initialize Vector Service components. Error: {e}")
    _chroma_client = None
    _collection = None
    _embedding_model = None

def add_documents_to_store(chunks: list[str], document_id: str) -> None:
    """
    Converts text chunks into vector embeddings and stores them in the ChromaDB collection
    with unique metadata tagging them to the document_id.
    
    Args:
        chunks (list[str]): A list of text chunks extracted from a document.
        document_id (str): A unique identifier for the document.
        
    Raises:
        RuntimeError: If the database or collection failed to initialize.
    """
    if _collection is None or _embedding_model is None:
        raise RuntimeError("Vector database or embedding model is not initialized.")

    if not chunks:
        print(f"No chunks provided for document {document_id}. Skipping.")
        return

    try:
        # Generate embeddings for the provided chunks
        embeddings = _embedding_model.encode(chunks).tolist()
        
        # Create unique IDs and metadata for each chunk
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"document_id": document_id, "chunk_index": i} for i in range(len(chunks))]
        
        # Add to the ChromaDB collection
        _collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully added {len(chunks)} chunks for document {document_id}.")
        
    except Exception as e:
        print(f"Error adding documents to store: {e}")
        raise

def query_similar_chunks(query: str, top_k: int = 6) -> list[str]:
    """
    Embeds the user's question, queries the ChromaDB collection for the top K 
    closest matches based on vector similarity, and returns the relevant text chunks.
    
    Args:
        query (str): The user's question or search query.
        top_k (int, optional): The number of top matching chunks to return. Defaults to 3.
        
    Returns:
        list[str]: A list of the most relevant text chunks.
        
    Raises:
        RuntimeError: If the database or collection failed to initialize.
    """
    if _collection is None or _embedding_model is None:
        raise RuntimeError("Vector database or embedding model is not initialized.")
        
    if not query.strip():
        return []

    try:
        # Generate embedding for the search query
        query_embedding = _embedding_model.encode([query]).tolist()
        
        # Query the ChromaDB collection
        results = _collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        
        # The results dictionary contains lists of lists for documents
        if results and 'documents' in results and results['documents']:
            # Since we only provided one query, we take the first list of matched documents
            return results['documents'][0]
            
        return []
        
    except Exception as e:
        print(f"Error querying similar chunks: {e}")
        return []
