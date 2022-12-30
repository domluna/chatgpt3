import os
import sqlite3
from enum import Enum

import dotenv

import fire
import openai


dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# taking from ChatGPT Javascript
# [
# 	{
# 		"id:"summarize",
# 		name:"Summarize",
# 		content:'Break down this content into a series of super short, simply written sections that follow a logical flow designed to help me understand the content as quickly as possible. Each section should include a "title" (1-5 words), the primary "content" (1-2 sentence), and an optional additional sentence for "detail" (1 sentence). The first section should provide a concise summary of the content.'
# 	},
# 	{
# 		id:"format",
# 		name:"Format",
# 		content:"(When responding to the following prompts, please make sure to properly style your response using Github Flavored Markdown. Use markdown syntax for things like headings, lists, tables, quotes, colored text, code blocks, highlights, superscripts, etc, etc. For emojis, use unicode. Make sure not to mention markdown or stying in your actual response.)\n"
# 	},
# 	{
# 		id:"code",
# 		name:"Programming question",
# 		content:B
# 	}
# ]
SUMMARIZE = """
Break down this conversation into 1) a title describing the entire conversation content and 2) a concise summary of the entire conversation (1-8 sentences). The summary should be written from the third-person prose of a thoughtful observer noting what User and ChatGPT talked about. Don't refer to the "thoughtful observer".

The format should be as follows:

Title: <title>

<summary>

{conversation}

Begin.

Title:"""

CODING_PROMPT = """
You are a brilliant and helpful coding assistant designed to help users with any programming-related questions or problems they may have.

As a programming expert, you have extensive knowledge about a variety of topics related to programming, including programming languages, syntax, debugging techniques, software design principles, code optimization, documentation, and more. No matter what programming challenges a user may be facing, however big or small, you will help them find an elegant solution. You are also happy to write code for users, even entire applications if its helpful!

Please respond in markdown format, making appropriate use of headers, numbered lists, tables, tagged code blocks, etc as needed. Code should be shared in markdown format either inline or as a code block, depending on length. Code blocks should make sure to specify the relevant programming language. Keep in mind that the code blocks you share will be rendered with a "copy code" button, so you may want to consider grouping code that is meant to be run together into one code block for easy copy and pasting.

Begin."""

GHOSTWRITER_PROMPT = """
You are a ghostwriter designed to help writers overcome writer's block.

As a expert ghostwriter, you have extensive knowledge about a variety of topics related to writing, including the structure of speeches, poetry, fictional, non-fictional, and more. You are also well aware of different styles of writing whether it be a person or a category. No matter what writing challenges a user may be facing, however big or small, you are happy to write for users, even entire chapters or scripts!

Write using the provided prompt and incorporating specific elements or themes as instructed. The goal is to create a cohesive and engaging piece of writing that showcases your ability to follow prompts and incorporate specific elements effectively.

Begin.
"""

FACTUAL_PROMPT = """
You are a factual assistant designed to help users with any questions or problems they may have related to facts, information, or research.

As a factual expert, you have extensive knowledge about a variety of topics and are able to provide accurate, reliable information on any subject that is within your scope. You are also skilled at researching and finding information on topics that may not be immediately familiar to you.

Please respond in markdown format, making appropriate use of headers, numbered lists, tables, and tagged code blocks as needed. If you are providing a list of facts or information, consider using bullet points or a table to make the information easy to read and understand.

Begin."""

USER_PROMPT = """
User: {user_input}

ChatGPT:"""

# enum for chat types
class ChatType(Enum):
    coding = 0
    ghostwriter = 1
    factual = 2

    def __str__(self):
        return self.name


DB_PATH = os.path.expanduser("~/.chatgpt3/chat.db")


def chatbot(chat_type=str(ChatType.factual), temperature=0.7, max_tokens=812):
    # create the directory for the database if it doesn't exist
    path = os.path.expanduser(DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS conversation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_type TEXT NOT NULL,
        conversation TEXT NOT NULL,
        summary TEXT NOT NULL,
        title TEXT NOT NULL
    )"""
    )
    conn.commit()

    # set the prompt based on `chat_type`
    if chat_type == str(ChatType.coding):
        prompt = CODING_PROMPT
    elif chat_type == str(ChatType.ghostwriter):
        prompt = GHOSTWRITER_PROMPT
    elif chat_type == str(ChatType.factual):
        prompt = FACTUAL_PROMPT
    else:
        raise ValueError("Invalid chat type")

    conversation = []

    print(
        f"You are starting a conversation with ChatGPT ({chat_type} mode). Type 'quit' to exit."
    )

    while True:
        try:
            # get user input from terminal
            user_input = input("Prompt:\n")
            if user_input == "quit":
                break

            prompt += "\n" + USER_PROMPT.format(user_input=user_input)
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            reply = response.choices[0]["text"]
            print("REPLY\n", reply)
            cc = USER_PROMPT.format(user_input=user_input) + reply
            conversation.append(cc)

            prompt += reply
            prompt.strip()
        except KeyboardInterrupt:
            print("Ending conversation")
            break

    if len(conversation) > 0:
        # turn `conversation` into a string
        conversation = "\n".join(conversation).strip()

        print("Summarizing the conversation...")
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=SUMMARIZE.format(conversation=conversation),
            max_tokens=max_tokens,
            temperature=temperature,
        )
        summary = response.choices[0]["text"]
        # title is the first line of `summary`
        title = summary.splitlines()[0]

        print("Saving the conversation to the database...")

        c.execute(
            """INSERT INTO conversation (chat_type, title, summary, conversation) VALUES (?, ?, ?, ?)""",
            (str(chat_type), title, summary, conversation),
        )
        conn.commit()

    conn.close()


if __name__ == "__main__":
    fire.Fire(chatbot)
