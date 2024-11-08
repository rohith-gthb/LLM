
############# Verification of query generated ############
############# Automate context refresh with config change############

import requests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from Chat2sql.config.config import *
import pandas as pd 
import json
import traceback as tb 


def process(response, get_context=True):
    data = '[' + response.text.strip().replace('\n', ',') + ']'
    json_data = json.loads(data)
    
    try:
        text = ''.join([node['response'] for node in json_data if not node.get('done', True)]).strip()
        time_taken = sum([node.get('total_duration', 0) for node in json_data]) / 1e9
        # t_min = int(time_taken // 60)
        # t_sec = round(time_taken % 60, 1)
        if get_context:
            return {'text': text, 'context': json_data[-1]['context'], 'time_taken': time_taken}
        return {'text': text, 'time_taken': time_taken}
    
    except Exception as e:
        # Print detailed traceback if an exception occurs
        print("Exception occurred:")
        print(''.join(tb.format_exception(type(e), e, e.__traceback__)))
        print("JSON data:", json_data)
        return {'text': '', 'context': ''}


def view_llm_response(response):
    # response = json.loads(response)
    print("{")
    for k, v in response.items():
        print('\t',k+":", v) 
    print("}")
    print('\n')


class LLMClient:

    retry_limit = 2

    def __init__(self, query_generate_context_file, query_validate_context_file, model_number = 0):
        self.model = ollama_models[model_number]
        print("~ ~ ~ ~ OLLAMA MODEL:",self.model)
        self.ollama_serve_port = 'http://localhost:11434/api/generate'
        self.query_generate_context_file = query_generate_context_file
        self.query_validate_context_file = query_validate_context_file

        if os.path.exists(self.query_generate_context_file):
            with open(self.query_generate_context_file, 'r') as file:
                self.gen_context = eval(file.read().strip())
            print(f"Re-loaded context from previous run using {self.query_generate_context_file} file...")
        else:
            json_data = {
                'prompt': generate_api_prompt,
                'model': self.model
            }
            response = requests.post(self.ollama_serve_port, json=json_data)
            processed_response = process(response=response, get_context=True)
            self.gen_context = processed_response.get('context', '')

            with open(self.query_generate_context_file, 'w') as file:
                file.write(str(self.gen_context))
            print(f"Generated new context and saved to {self.query_generate_context_file} file.")

        if os.path.exists(self.query_validate_context_file):
            with open(self.query_validate_context_file, 'r') as file:
                self.val_context = eval(file.read().strip())
            print(f"Re-loaded context from previous run using {self.query_validate_context_file} file...")
        else:
            json_data = {
                'prompt': validate_api_prompt,
                'model': self.model
            }
            response = requests.post(self.ollama_serve_port, json=json_data)
            processed_response = process(response=response, get_context=True)
            self.val_context = processed_response.get('context', '')

            with open(self.query_validate_context_file, 'w') as file:
                file.write(str(self.val_context))
            print(f"Generated new context and saved to {self.query_validate_context_file} file.")

    def verify_query(self, response, model=None): 
        model = model if model else self.model
        # print(response)
        # print(type(response))
        Tags = response['Tags']
        query = response['Query']
        gen_time_taken = response['gen time taken']
        sql_question = response['prompt']
        prompt = f"Question:\n{sql_question}\n\nAnswer:\n{query}\n\nPlease verify the above query"
        json_data = {
            "model": model,
            "prompt": prompt,
            "context": self.val_context,
            "stream": True,
            "verbose": True
        }
        query_valid_response = requests.post(self.ollama_serve_port, json=json_data)
        query_valid_response = process(query_valid_response, get_context=False)
        return_dict = json.loads(query_valid_response['text'])
        return_dict['val time taken'] = query_valid_response['time_taken']
        return_dict['gen time taken'] = gen_time_taken
        return_dict['Query'] = query
        return_dict['Tags'] = Tags
        return return_dict

    def ask_llm(self, prompt, model=None, counter=0, comment=""):
        if counter>self.retry_limit:
            return {} 
        if comment!='':
            print('Comment recieved..... trying to rectify the response...')
        model = model if model else self.model
        json_data = {
            "model": model,
            "prompt": prompt,
            "context": self.gen_context,
            "stream": True,
            "verbose": True
        }
        try:
            response = requests.post(self.ollama_serve_port, json=json_data)
            response = process(response, get_context=False)
            # print("\n##################")
            # print("LINE 129")
            # print(response)
            # print("##################\n")
            processed_response = json.loads(response['text'])
            processed_response['model'] = self.model
            processed_response['prompt'] = prompt
            processed_response['gen time taken'] = response['time_taken']
            processed_response = self.verify_query(processed_response)
            view_llm_response(processed_response)
            if(str(processed_response['Query valid']).lower()=='false'):
                new_comment = "In your previous attempt this is the reason why it went wrong '"+processed_response['Comment']+"'. Please rectify it now."
                return self.ask_llm(prompt, counter=counter+1, comment=comment+new_comment)
        except Exception as e:
            print(''.join(tb.format_exception(None, e, e.__traceback__)))
            print("Retrying.......... :)")
            return self.ask_llm(prompt, counter=counter+1)
        return processed_response

# Example usage:
llm_client = LLMClient(model_number=0, query_generate_context_file=query_generate_context, query_validate_context_file=query_validate_context)
prompts_list = [
    "Get me distinct brands from Aug 2023", 
    "What are the top 5 performing brands in the year 2024?", 
    "Get me aggregated sales value for brands each month and their contributions in percentage rounded to 2 digits witin the respective month.",
    "Which brands have shown more than 100%% growth in sales in the past 6 months from current month 92024"
    ]

try:
    csv_log = pd.read_csv(csv_log_file_path)
except:
    csv_log = pd.DataFrame(columns=['model', 'prompt', 'Query', 'Query valid', 'Comment', 'Tags', 'val time taken', 'gen time taken'])

for prompt in prompts_list:
    print("Generating prompt for the question:\n*", prompt)
    test_response = llm_client.ask_llm(prompt)
    # print(test_response['text'])
    # print(type(test_response))
    csv_log = pd.concat([csv_log, pd.DataFrame([test_response])])
    csv_log.to_csv(csv_log_file_path, index=False)
