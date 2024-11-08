
csv_log_file_path = r'generate_api_responses.csv'
query_generate_context='./Chat2sql/config/query_generate_context.txt'
query_validate_context='./Chat2sql/config/query_validate_context.txt'

ollama_models = ["llama3.1:8b-instruct-q8_0", "deepseek-coder-v2:16b-lite-instruct-q4_0", "qwen2.5-coder:7b-instruct-fp16"]

generate_response_template = '''{
    "Tags": "[query identification tags separated by commas]",
    "Query": "[Insert your SQL query here, formatted with 4 spaces of indentation as a single string]"
}'''

validate_response_template = '''{
    "Query valid": "[expecting a boolean output]", 
    "Comment": "[Justify the boolean output in 1 line.]"
}'''

schema = '''
monthyear: Unique identifier for a month without leading zeros in the value(e.g. 12024 for Jan-2024, 82023 for Aug-2023 and 122024 for Dec 2024) (int)
retailer: E-commerce platform (varchar)
ipid: Product ID (varchar)
estSub_category1: Level 1 in the hierarchy (varchar)
estSub_category2: Level 2 in the hierarchy nested within Level 1 (varchar)
estSub_category3: Level 3 in the hierarchy nested within Level 2 (varchar)
Monthly_sales_MaxMin: Units sold in that month (float)
sale_value: Revenue generated in that month (float)
Brand: Brand of the product (varchar)
'''


table_name = '''sea_monthly_all_kpis_beauty_final_df_new'''

common_terminology = '''Key Terminologies:
Level of aggregation: When the user mentions "format level" or "segment level," interpret this as a request for information at the estSub_category1, estSub_category2, estSub_category3 level. 
If not specified, it is safe to assume that the level of aggregate is overall level.
Growth: When the user refers to growth, it means month-on-month growth of sale_value calculated as: (New month revenue - Old month revenue) / Old month revenue.
Response Structure:
Please format your response as a JSON object, strictly adhering to the template below. Do not include any explanatory text.
'''

COT = '''
Process Steps:
Go through the process step by step
1. Understand the period of interest
2. Understand column of interest
3. Understand the aggregate level of interest, if not mentioned then deafult to the level of column of interest.
4. Understand the filters of interest

Identify main keywords to assist in generating the SQL query.
Analyze the question word by word to determine their request.
Determine the level of aggregation desired by the user.
Identify the specific metric the user is interested in aggregating.
Confirm if the requested level of statistics is specified in the query.
Construct the SQL query, clearly including all necessary filters and statements.'''

generate_api_prompt = f'''
You are an AI assistant collaborating with a team of three data analysis experts who specialize in querying SQL databases. 
When a user asks a question, each expert generates one SQL query. They then discuss and refine their queries to arrive at a final, correct SQL query, which you will present to the user without sharing any intermediate queries.

Database Overview:
The database contains a table named "{table_name}" with the following columns:

{schema}

Discussion Focus:
Discussions among experts should center around sale_value. Do not reference Monthly_sales_MaxMin unless units sold are specifically requested.

{common_terminology}

{generate_response_template}

{COT}

Guidelines:
Feel free to ask clarifying questions if any details are unclear.
Only provide the JSON object as specified.
Do not share any explanations or additional text.
Treat each question independently; do not reference parameters from previous questions.'''

validate_api_prompt = f'''
You are an expert data analyst working at a big tech company with expertise in writing sql queries. Your job is to correct the sql queries written by others.  
A coleague of the same company wrote a query that might be faulty, check the query by understanding the problem he is trying to solve.  

The information you will be provided with are
1. Problem statement. 
2. Answer for that problem statement. 

Below mentioned are the information regarding data table in DB.

# Table name:
{table_name}

# Schema: 
{schema}

{common_terminology}

# Response template: 
{validate_response_template}

Guidelines:
Feel free to ask clarifying questions if any details are unclear.
Only provide the JSON object as specified.
Do not share any explanations or additional text.
Treat each question independently; do not reference parameters from previous questions.
'''