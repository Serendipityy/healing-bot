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
                # Format answers with best answer marking
                answers_list = row['answers']
                best_answer = str(row['best_answer']).strip()
                
                if answers_list and best_answer:
                    formatted_answers = []
                    best_found = False
                    
                    for answer in answers_list:
                        answer_str = str(answer).strip()
                        # Check if this answer matches the best answer
                        if answer_str == best_answer or (len(answer_str) > 50 and best_answer in answer_str):
                            formatted_answers.append(f"⭐ BEST: {answer_str}")
                            best_found = True
                        else:
                            formatted_answers.append(f"- {answer_str}")
                    
                    # If best answer wasn't found in the list, add it at the top
                    if not best_found:
                        formatted_answers.insert(0, f"⭐ BEST: {best_answer}")
                    
                    answers_text = "\n".join(formatted_answers)
                else:
                    # Fallback if no answers list or best answer
                    answers_text = f"⭐ BEST: {best_answer}" if best_answer else "No answers available"

                content = f"""Question: {row['question']}

Answers:
{answers_text}"""
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
    
def load_summary_documents_from_excel(excel_path: Path = None) -> List[Document]:
    if excel_path:
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel file not found at {excel_path}")
        
        logging.info(f"Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path)

        if 'summary' not in df.columns or 'labels' not in df.columns:
            raise ValueError("Excel file must contain 'summary' and 'labels' columns.")
        
        documents = []
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            for _, row in batch.iterrows():
                summary_text = row['summary']
                doc = Document(
                    page_content=str(summary_text).strip(),
                    metadata={"labels": row['labels'], "source": str(excel_path)}
                )
                documents.append(doc)

        return documents
    else:
        raise ValueError("Excel path is required for loading documents.")