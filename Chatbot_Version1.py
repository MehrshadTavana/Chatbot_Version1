import os
import pandas as pd
import openai
from openai import OpenAI
import numpy as np
import ast

openai.api_key = "sk-kttTQMKBHSSkx5qs1GzEF3"
openai.api_base = "https://proxy.fuelix.ai/v1"
os.environ["OPENAI_API_BASE"] = "https://proxy.fuelix.ai/v1"
client = OpenAI(api_key = openai.api_key, base_url = openai.api_base)

df = pd.read_csv("clean_scraped_updated_version#2.csv")
df["embedding_clean_version_2"] = df["embedding_clean_version_2"].apply(ast.literal_eval)


def get_embedding(text, model="text-embedding-3-large"):
   text = text.replace("\n", " ")
   return client.embeddings.create(input = [text], model=model).data[0].embedding

def distances_from_embeddings(embedding1, embeddings2, distance_metric="cosine"):
    distances = []
    for embedding2 in embeddings2:
        # Compute cosine distance between embeddings
        distance = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        distances.append(distance)
    return distances

def get_rows_sorted_by_relevance(question, df):
    question_embedding = get_embedding(question)
    distances = distances_from_embeddings(question_embedding, df["embedding_clean_version_2"].values)
    df_copy = df.copy()
    df_copy["distances"] = distances
    df_copy.sort_values("distances", ascending=False, inplace=True)
    return df_copy, distances

def process_query(query, df):
    province_list = [
    "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador", 
    "Northwest Territories", "Nova Scotia", "Nunavut", "Ontario", "Prince Edward Island", 
    "Quebec", "Saskatchewan", "Yukon"]
    
    df_search_storage_level_1 = pd.DataFrame({'Organization_Name': [],'Title': [],'Descripts': [],'M/F/S/Y/YP/U	': [],
    'Status': [],'URL': [],'How_it_works': [],'Type': [],'Minimum Money': [],'Maximum Money': [],'Funding Limits': [],
    'Stacking': [],'You': [],'Your Project': [],'Use this to': [],' ': [],'scraped_URL_Content': [],'clean_scraped': [],
    'embedding_clean': [],'industry': [],'location': [],'stage': [],'Organization_name_without_program': [],'Programs': [],
    'clean_scraped_version_2': [],'embedding_clean_version_2': []
    })

    df_search_storage_level_2 = df_search_storage_level_1

    for province in province_list:
        if province.lower() in query.lower():
            df_search_storage_level_1 = pd.concat([
                df[df['location'].str.contains(province, case=False, na=False)],
                df_search_storage_level_1
            ])

            if ('grant' or 'Grant') in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Grant"])],
                    df_search_storage_level_2
                ])
            elif ('loan' or 'Loan') in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Loan"])],
                    df_search_storage_level_2
                ])
            elif ("Tax" or "tax") in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Tax Credits"])],
                    df_search_storage_level_2
                ])
            elif ("Wage" or "wage" or "subsidies" or "Subsidies") in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Wage Subsidies"])],
                    df_search_storage_level_2
                ])
            elif ("Advice" or "advice") in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Advice"])],
                    df_search_storage_level_2
                ])
            elif ("Partnerships" or "partnerships" or "partnership" or "Partnership") in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Partnerships"])],
                    df_search_storage_level_2
                ])
            elif ("Research" or "research") in query:
                df_search_storage_level_2 = pd.concat([
                    df_search_storage_level_1[df_search_storage_level_1["Type"].isin(["Research"])],
                    df_search_storage_level_2
                ])
            else:
                df_search_storage_level_2 = pd.concat([df_search_storage_level_1, df_search_storage_level_2])

    return df_search_storage_level_2

GPT_MODEL = "gpt-4o-mini"
def chat_system():
    response_bank = []
    while True:
        query = input("Welcome to the chatbot. Please enter your prompt (or type 'exit' to quit or type 'new chat' to start a new chat): ").strip()
        if query.lower() == 'new chat':
            chat_system()
        if query.lower() == 'exit':
            print("Thank you for using the system. Goodbye!")
            break

        print("\nProcessing your request...\n")
        query = query + ' please only provide English results.' + 'if my prompt is not related to the information that you have, please tell me to refine it and do not give me any information.'
        df_search_level_2 = process_query(query,df)

        # Sort the results by relevance
        new_df, distances = get_rows_sorted_by_relevance(query, df_search_level_2)
        numin = str(new_df.head(3).clean_scraped_version_2.values[0]) + "\n\n" + f"{'--------' * 50}" + "\n" + str(new_df.head(3).clean_scraped_version_2.values[1]) + "\n\n" + f"{'--------' * 50}" + "\n" + str(new_df.head(3).clean_scraped_version_2.values[2])

        top_results = new_df.head(3)

        messages = [
            {"role": "system", "content": (
                "Find and add the funding amount (in dollars) immediately after the type with nextline for each program, following the format: Funding Amount: [amount in Dollar]. Please ensure that no information is deleted or omitted in any part of the given prompt. The goal is to enrich the entries with valuable details, while preserving the full integrity of the original content. Also organize the Additional Description if its text needs any space between the words. please help the user based on the following information."
            )},
            {"role": "user", "content": numin},
        ]

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=0,
            # stream=True
        )

        response_message = response.choices[0].message.content
        response_bank.append(response_message)
        print("\n")
        print(response_message)
        print("\n" + "="*80 + "\n")
        i = 0
        response_pass = ''
        while True:
          query = input("Please enter your prompt about the recommended results (or type 'exit' to quit or type 'new chat' to start a new chat): ").strip()
          if query.lower() == 'new chat':
              chat_system()
          if query.lower() == 'exit':
              print("Thank you for using the system. Goodbye!")
              break

          print("\nProcessing your request...\n")
          query = query

          # Sort the results by relevance
          new_df, distances = get_rows_sorted_by_relevance(query, df_search_level_2)
          numin = str(new_df.head(3).clean_scraped_version_2.values[0]) + "\n\n" + f"{'--------' * 50}" + "\n" + str(new_df.head(3).clean_scraped_version_2.values[1]) + "\n\n" + f"{'--------' * 50}" + "\n" + str(new_df.head(3).clean_scraped_version_2.values[2])
          top_results = new_df.head(3)

          for resp in response_bank:
            response_pass = str(response_pass) + str(resp) + '\n'

          messages = [
              {"role": "system", "content": (
                  'please help the user based on the following information. if you could not find any answer for the prompt of the user, please tell him to refine his prompt to have a better result.' + response_pass
              )},
              {"role": "user", "content": query},
          ]

          response = client.chat.completions.create(
              model=GPT_MODEL,
              messages=messages,
              temperature=0,
              # stream=True
          )

          response_message = response.choices[0].message.content
          response_bank.append(response_message)
          print("\n")
          print(response_message)
          print("\n" + "="*80 + "\n")
        break

# Run the chat system
chat_system()