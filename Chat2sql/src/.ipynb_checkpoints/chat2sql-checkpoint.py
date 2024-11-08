
############# Verification of query generated ############
############# Automate context refresh with config change############

import requests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from Chat2sql.config.config import *
import pandas as pd 
import json
import traceback


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
        print(''.join(traceback.format_exception(type(e), e, e.__traceback__)))
        print("JSON data:", json_data)
        return {'text': '', 'context': ''}


def view_llm_response(response):
    response = json.loads(response['text'])
    for k, v in response.items():
        print("##############")
        print(k, v) 
        print()



class LLMClient:

    retry_limit = 2

    def __init__(self, context_file, model_number = 0):
        self.model = ollama_models[model_number]
        print("~ ~ ~ ~ OLLAMA MODEL:",self.model)
        self.ollama_serve_port = 'http://localhost:11434/api/generate'
        self.context_file = context_file

        if os.path.exists(self.context_file):
            with open(self.context_file, 'r') as file:
                self.GLOBAL_CONTEXT = eval(file.read().strip())
            print(f"Re-loaded context from previous run using {self.context_file} file...")
        else:
            json_data = {
                'prompt': generate_api_prompt,
                'model': self.model
            }
            response = requests.post(self.ollama_serve_port, json=json_data)
            processed_response = process(response=response, get_context=True)
            self.GLOBAL_CONTEXT = processed_response.get('context', '')

            # Save the context to a file for future use
            with open(self.context_file, 'w') as file:
                file.write(str(self.GLOBAL_CONTEXT))
            print("Generated new context and saved to file.")

    def ask_llm(self, prompt, model=None, counter=0):
        if counter>self.retry_limit:
            return {} 
        model = model if model else self.model
        json_data = {
            "model": model,
            "prompt": prompt,
            "context": self.GLOBAL_CONTEXT,
            "stream": True,
            "verbose": True
        }
        response = requests.post(self.ollama_serve_port, json=json_data)
        response = process(response, get_context=False)
        print(response)
        try:
            processed_response = json.loads(response['text'])
            processed_response['model'] = self.model
            processed_response['prompt'] = prompt
            processed_response['time taken'] = response['time_taken']
            print('processed_response:', '\n',processed_response)
        except:
            print("Retrying.......... :)")
            return self.ask_llm(prompt, counter=counter+1)
        return processed_response

# Example usage:
llm_client = LLMClient(model_number=0, context_file=context_file)
prompts_list = [
    "Get me distinct brands from Aug 2023", 
    "What are the top 5 performing brands in the year 2024?", 
    "Get me aggregated sales value for brands each month and their contributions witin the respective month.",
    "Which brands have shown more than 100%% growth in sales in the past 6 months from current month 92024"
    ]

try:
    csv_log = pd.read_csv(csv_log_file_path)
except:
    csv_log = pd.DataFrame(columns=['model', 'prompt', 'Query', 'Tags', 'time taken'])

for prompt in prompts_list:
    print("Generating prompt for the question:", prompt)
    test_response = llm_client.ask_llm(prompt)
    # print(test_response['text'])
    print(type(test_response))
    csv_log = pd.concat([csv_log, pd.DataFrame([test_response])])
    csv_log.to_csv(csv_log_file_path, index=False)
