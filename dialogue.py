from langchain_ollama import OllamaLLM
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

HISTORY_LENGTH = 100
TEMPERATURE = 0.5
MODELS = ["llama3.2:1b", "llama3.2"]
MODEL = 1

class Model():
    def __init__(self, language="français") -> None:
        self.language = language
        self.history = []

        # Get model
        model = OllamaLLM(model=MODELS[MODEL], temperature=TEMPERATURE)

        # Define behaviour
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Tu es un système qui engage des conversations avec l'utilisateur afin qu'il apprenne {language}. Tu parles en {language}. Tu es gentil et énergique. Tu es ouvert à parler de nombreux sujets. Vérifie si l'utilisateur fait des erreurs grammaticales lorsqu'il parle et essaie de les corriger subtilement en continuant la conversation. Par exemple, tu peux répéter ce qu'il a dit dans le cadre de ta phrase de manière naturelle. Ne corrige pas trop. Ignore les erreurs grammaticales moins importantes qu'il fait. Si l'erreur grammaticale est très importante, tu peux la signaler et la corriger directement, mais toujours continuer la conversation. Encourage l'utilisateur à parler. Sois bref dans tes réponses. Il doit parler plus que toi pour apprendre. Commence par te présenter."),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{query}")
            ]
        )

        self.chain = prompt | model

    def process(self, query: str) -> str:
        output = self.chain.invoke(
            {
                "language": self.language,
                "history": self.history,
                "query": query
            })
        self.history.append(HumanMessage(content=query))
        self.history.append(AIMessage(content=output))
        if len(self.history) > HISTORY_LENGTH:
            self.history.pop[0]
        return output
    
    # Only for testing
    def stream(self, query: str) -> None:
        output = ""
        for chunk in self.chain.stream(
            {
                "language": self.language,
                "history": self.history,
                "query": query
        }):
            #if isinstance(chunk, AIMessage):
            print(chunk, end="", flush=True)

            output += chunk
        self.history.append(HumanMessage(content=query))
        self.history.append(AIMessage(content=output))
        if len(self.history) > HISTORY_LENGTH:
            self.history.pop[0]
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