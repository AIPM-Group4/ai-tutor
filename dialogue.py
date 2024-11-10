import os
from openai import OpenAI
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

HISTORY_LENGTH = 100
MODEL = "gpt-4o"  # You can change this to other OpenAI models as needed

class Model():
    def __init__(self, language="english", system_prompt=None) -> None:
        self.language = language
        self.history = []

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )  # Make sure to set your API key in the environment variable

        # Define behaviour
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = (
                "You should output your response in this format: <response> | <list of errors and their corrections>. "
                "You are a French native speaker speaking with a user who is learning French. You are a helpful assistant."
            )

    def process(self, query: str) -> str:
        messages = [{"role": "system", "content": self.system_prompt.format(language=self.language)}]
        messages.extend(
            [{"role": "user" if i % 2 == 0 else "assistant", "content": msg.content} for i, msg in enumerate(self.history)]
        )
        messages.append({"role": "user", "content": query})

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        output = response.choices[0].message.content

        self.history.append(HumanMessage(content=query))
        self.history.append(AIMessage(content=output))
        if len(self.history) > HISTORY_LENGTH:
            self.history.pop(0)
        
        if "|" in output:
            response_text, errors = output.split("|")
            return response_text.strip(), errors.strip()
        else:
            return output.strip(), ""
