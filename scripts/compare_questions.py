import pandas as pd

def find_unique_questions(file1, file2, output_file):
    # Load the Excel files
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)

    # Ensure the 'question' column exists in both files
    if 'question' not in df1.columns or 'question' not in df2.columns:
        raise ValueError("Both files must contain a 'question' column.")

    # Find rows in df1 that are not in df2 based on the 'question' column
    unique_questions = df1[~df1['question'].isin(df2['question'])]

    # Save the result to a new Excel file
    unique_questions.to_excel(output_file, index=False)
    print(f"Unique questions saved to {output_file}")

if __name__ == "__main__":
    file1 = "data/generated_test_dataset_question_answers_best_answer_final.xlsx"
    file2 = "data/test_data_context_answer/merged_test_output.xlsx"
    output_file = "data/unique_questions.xlsx"

    find_unique_questions(file1, file2, output_file)
