import os
from pypdf import PdfReader

def extract_text_from_pdf(file_path: str) -> str:
    """
    Reads a PDF file and extracts all text page by page.
    
    Args:
        file_path (str): The path to the PDF file.
        
    Returns:
        str: The extracted text from the entire PDF.
    """
    if not os.path.exists(file_path):
        print(f"Error: PDF file not found at path: {file_path}")
        return ""
        
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        
    return text

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Splits the extracted text into manageable chunks.
    Ensures that words are not cut in half and that the overlap is maintained.
    
    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The maximum number of characters per chunk.
        overlap (int): The number of overlapping characters between consecutive chunks.
        
    Returns:
        list[str]: A list of text chunks.
    """
    if not text.strip():
        return []
        
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be strictly greater than overlap")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        
        # If we exceed the text length, we can just take the rest
        if end >= text_length:
            chunks.append(text[start:].strip())
            break
            
        # Find the last space within the chunk to avoid cutting a word at the end
        last_space_end = text.rfind(' ', start, end)
        if last_space_end != -1 and last_space_end > start:
            end = last_space_end
            
        chunks.append(text[start:end].strip())
        
        # Calculate the next start position
        next_start_raw = end - overlap
        
        # Ensure we don't cut a word at the beginning of the next chunk
        # Find the next space after next_start_raw
        next_space_start = text.find(' ', next_start_raw)
        
        if next_space_start != -1 and next_space_start < end:
            start = next_space_start + 1
        else:
            # Fallback if no space is found
            start = next_start_raw
            
        # Safeguard to guarantee forward progress
        if start >= end:
            start = end
            
    return chunks
