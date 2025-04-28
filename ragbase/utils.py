import ast
import logging
from pathlib import Path
from typing import List

import pandas as pd
from langchain_core.documents import Document


def safe_parse_answers(x):
    try:
        if isinstance(x, str):
            # Giữ lại \n nhưng escape đúng để literal_eval hiểu được
            escaped = x.encode('unicode_escape').decode('utf-8')
            return ast.literal_eval(escaped)
        return x
    except Exception as e:
        print(f"[!] Lỗi khi parse: {x} -> {e}")
        return []


def load_documents_from_excel(excel_path: Path = None) -> List[Document]:
    if excel_path:
        # Read and process Excel file
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel file not found at {excel_path}")
        
        logging.info(f"Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path)
        
        df['answers'] = df['answers'].apply(safe_parse_answers)
        
        # Create documents
        documents = []
        batch_size = 1000  # Process 1000 rows at a time
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            for _, row in batch.iterrows():
                # Format answers
                answers_list = row['answers']
                formatted_answers = "\n- " + "\n- ".join(answers_list) if answers_list else "No answers available"

                content = f"""Question: {row['question']}\nBest answer: {row['best_answer']}\nAnswers:{formatted_answers}"""
                doc = Document(
                    page_content=content,
                    metadata={"labels": row['labels'], "source": str(excel_path)}
                )
                documents.append(doc)
                # logging.info(f"Processed {len(documents)} documents")
        return documents
    else:
        raise ValueError("Excel path is required for loading documents.")
        return []