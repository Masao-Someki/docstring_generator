import os
from openai import OpenAI


os.environ['OPENAI_API_KEY'] = "YOUR API KEY HERE"


SYS_PROMPT = """
You are an accomplished programmer with expertise in various programming languages, including Python.
Your task is to write a sophisticated, well-documented docstring for a given Python function or class.
You must adhere to the Google Python Style Guide and PEP 8 standards.
It is preferred to include examples in your docstring to illustrate the functionality of the function or class.

You are allowed to use the following fields for your docstring:
- Attributes
- Args
- Returns
- Yieds
- Raises
- Examples
- Note
- Todo
"""

class ChatGPT:
    def __init__(self):
        # CHATGPT-definition
        self.MODEL="gpt-4o-mini"
        self.client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    
    def __call__(self, prompt):
        completion = self.client.chat.completions.create(
            model=self.MODEL,
            temperature=1.0,
            top_p=0.8,
            messages=[
                {"role": "system", "content": SYS_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
