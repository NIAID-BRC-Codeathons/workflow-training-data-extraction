#
# A wrapper class for the Argonne Argo LLM service
#

import os
import requests
import json

MODEL_GPT35 = "gpt35"
MODEL_GPT4 = "gpt4"
MODEL_GPT4T = "gpt4turbo"

DEFAULT_ARGO_URL = 'http://lambda5.cels.anl.gov:44497/v1/chat'

class ArgoWrapper:
    def __init__(self, 
                 url = None, 
                 model = "gpt4o", 
                 user = 'tandoc')-> None:
        self.url = url if url else DEFAULT_ARGO_URL
        self.model = model
        self.user = user

    def invoke(self, prompt_system: str, prompt_user: str, temperature: float = 0.0, top_p: float = 0.95):
        headers = {
            "Content-Type": "application/json"
        }
        data = {
                "user": self.user,
                "model": self.model,
                "system": prompt_system,
                "prompt": [prompt_user],
                "stop": [],
                "temperature": temperature,
                "top_p": top_p
        }
        # print(f"[DEBUG] Calling Argo with temperature={temperature}, top_p={top_p}")
        # Log the payload for debugging
        # print(f"DEBUG: Payload being sent to Argo:\n{json.dumps(data, indent=2)}")
            
        data_json = json.dumps(data)    
        response = requests.post(self.url, headers=headers, data=data_json)

        if response.status_code == 200:
            parsed = json.loads(response.text)
            return parsed
        else:
            raise Exception(f"Request to {self.url} failed with status code: {response.status_code} and message: {response.text}")

class ArgoEmbeddingWrapper:
    def __init__(self, url = None, user = os.getenv("USER")) -> None:
        self.url = url if url else DEFAULT_ARGO_URL
        self.user = user
        #self.argo_embedding_wrapper = argo_embedding_wrapper

    def invoke(self, prompts: list):
        headers = { "Content-Type": "application/json" }
        data = {
            "user": self.user,
            "prompt": prompts
        }
        data_json = json.dumps(data)
        response = requests.post(self.url, headers=headers, data=data_json)
        if response.status_code == 200:
            parsed = json.loads(response.text)
            return parsed
        else:
            raise Exception(f"Request failed with status code: {response.status_code}")

    def embed_documents(self, texts):
        return self.invoke(texts)

    def embed_query(self, query):
        return self.invoke(query)[0]
