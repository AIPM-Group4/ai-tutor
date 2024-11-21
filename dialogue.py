import os
from openai import OpenAI
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv()

HISTORY_LENGTH = 100
MODEL = "gpt-4o-mini"  # You can change this to other OpenAI models as needed

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
                """
                Play the role of a French language tutor. As a native French speaker, you will be speaking with someone who wants to improve their French skills through a simulated conversation. Imagine you met someone at a social event in France, and you don't know anything about them. Start by introducing yourself in French, and then respond to their questions and initiate topics of conversation. 
                Additionally, develop a response generation strategy for introducing subtle corrections to your answers when the provided information is unclear or incorrect.
                Memorize any mistakes made during the conversation and provide a comprehensive report of errors at the conclusion of the discussion, detailing the corrections and explanations for the corrections. Go!

                NOTES:
                - Do not wait for the user to start speaking. Start by introducing yourself in French, and then respond to their questions and initiate topics of conversation. 
                - You should output your response in this format: <response> | <list of errors and their corrections>.
                - Write as you would speak. Be conversational and informal.
                - Provide concise responses, and adapt your tone and language to the level of the person you're speaking with.
                - You should not ask more than 2 questions on the same topic.
                - You should be engaging in the conversation by saying your opinion (do not do this every time you answer. Spice it up!).
                - You should be engaging in the conversation by telling anecdotes that happened to you (do not do this every time you answer. Spice it up!).
                - Ignore character errors such as using 'c' instead of 'ç' or oe instead of œ.
                """
            )

    def first_interaction(self) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        output = response.choices[0].message.content

        self.history.append(AIMessage(content=output))

        if "|" in output:
            texts = output.split("|")
            return texts[0].strip()
        else:
            return output.strip()

    def process(self, query: str) -> tuple[str, str]:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(
            [{"role": "assistant" if (len(self.history) - 1 - i) % 2 == 0 else "user", "content": msg.content} for i, msg in enumerate(self.history)]
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
            aux = output.split("|")
            if len(aux) > 1:
                return aux[0].strip(), aux[1].strip()
            else:
                return aux[0].strip(), "No error detected"
        

    def feedback(self, chat_history: list[dict[str, str]]) -> dict[str, str]:
        # generate the feedback based on the chathistory
        content = """
        This is a feedback summary
        You should add feedback based on the conversation {chat_history}
        You should add the following;
        1. Conversation Summary
        2. Compliments for users based on the conversation
        3. Grammatical Feedback
        4. Suggestions for Future Practice
        """
        messages = [{"role": "system", "content": content}]
        
        messages.extend(
            [{"role": "assistant" if i % 2 == 0 else "user", "content": msg["text"]} for i, msg in enumerate(chat_history)]
        )
        messages.append({"role": "assistant", "content": "Finish Conversation"})
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        output = response.choices[0].message.content
        self.history.extend([HumanMessage(content=msg["text"]) for msg in chat_history])
        self.history.append(AIMessage(content=output))
        if len(self.history) > HISTORY_LENGTH:
            self.history.pop(0)
        return output


# For testing
def main():
    m = Model()

    print(m.first_interaction())
    query = input(">> ")
    while query != "/bye":
        print()
        output, errors = m.process(query)
        print(output + "\n")
        print("[errors: " + errors + "]")
        print("\n")
        #print([{"role": "assistant" if (len(m.history) - 1 - i) % 2 == 0 else "user", "content": msg.content} for i, msg in enumerate(m.history)])
        query = input(">> ")


if __name__ == "__main__":
    main()
