import os
from openai import OpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
        # self.system_prompt = "Tu es un système qui engage des conversations avec l'utilisateur afin qu'il apprenne {language}. Tu parles en {language}. Tu es gentil et énergique. Tu es ouvert à parler de nombreux sujets. Vérifie si l'utilisateur fait des erreurs grammaticales lorsqu'il parle et essaie de les corriger subtilement en continuant la conversation. Par exemple, tu peux répéter ce qu'il a dit dans le cadre de ta phrase de manière naturelle. Ne corrige pas trop. Ignore les erreurs grammaticales moins importantes qu'il fait. Si l'erreur grammaticale est très importante, tu peux la signaler et la corriger directement, mais toujours continuer la conversation. Encourage l'utilisateur à parler. Sois bref dans tes réponses. Il doit parler plus que toi pour apprendre. Commence par te présenter."
        self.system_prompt = "You should output you response in this format: <response> | <list of errors and their corrections>. You are a French native speaker speaking with a user who is learning French. You are a helpful assistant. You should output you response in this format: <response> | <list of errors and their corrections>."

    def process(self, query: str) -> str:
        messages = [{"role": "system", "content": self.system_prompt.format(language=self.language)}]
        messages.extend([{"role": "user" if i % 2 == 0 else "assistant", "content": msg.content} for i, msg in enumerate(self.history)])
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
            response, errors = output.split("|")
            return response, errors
        else:
            return output, ""
    
    # Only for testing
    def stream(self, query: str) -> None:
        messages = [{"role": "system", "content": self.system_prompt.format(language=self.language)}]
        messages.extend([{"role": "user" if i % 2 == 0 else "assistant", "content": msg.content} for i, msg in enumerate(self.history)])
        messages.append({"role": "user", "content": query})

        output = ""
        for chunk in self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True
        ):
            if chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="", flush=True)
                output += chunk.choices[0].delta.content

        self.history.append(HumanMessage(content=query))
        self.history.append(AIMessage(content=output))
        if len(self.history) > HISTORY_LENGTH:
            self.history.pop(0)
        return output
    
# Only for testing
def main():
    m = Model()
    query = input(">> ")
    while query != "/bye":
        print()
        m.stream(query)
        print("\n")
        query = input(">> ")


if __name__ == "__main__":
    main()
