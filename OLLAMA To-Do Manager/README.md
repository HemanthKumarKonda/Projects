To-Do Manager Bot

### Built using concepts from “ChatGPT Prompt Engineering for Developers”

Overview

The To-Do Manager Bot is an interactive conversational assistant built with Python that helps users manage their daily tasks in a natural, chat-like interface.
This project demonstrates how Large Language Models (LLMs) can be integrated with a lightweight Python GUI framework (Panel) to create context-aware and user-friendly bots.

The idea for this project came from applying what I learned in the ChatGPT Prompt Engineering for Developers course, where I explored how prompt structure, system roles, and message memory affect an AI assistant’s behavior.

---

Features

✅ Conversational Task Management – Add, view, and delete tasks through simple chat commands.
✅ Context Awareness – The bot remembers previous messages during a session.
✅ Real-Time Task List – Displays an updated list of tasks every time you interact with the bot.
✅ Lightweight Interface – Built using Panel, a Python library for creating interactive GUIs.
✅ Customizable Prompts – Modify the system prompt to change the bot’s tone or purpose (e.g., convert it into a Library FAQ bot, Pizza Order bot, etc.).

---

Tech Stack

 Python 3.x
 Panel – For interactive chat UI
 Ollama or OpenAI API – For generating conversational responses
 dotenv – For secure API key management

---

Core Concepts Demonstrated

 System & user role separation in prompt design
 Stateful conversation handling using message history
 Prompt engineering for guided task-specific responses
 Building a simple GUI around an LLM without heavy frameworks

---

Project Structure

```
├── ToDo_Bot.ipynb        # Main Jupyter notebook with bot logic
├── .env                  # Stores API key securely
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
```

---

How to Run

1. Clone the repository

   ```bash
   git clone https://github.com/<your-username>/ToDo-Manager-Bot.git
   cd ToDo-Manager-Bot
   ```

2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment

    Create a `.env` file and add your OpenAI key:

     ```
     OPENAI_API_KEY=your_api_key_here
     ```
    (Optional) If using Ollama, make sure it’s installed and running locally.

4. Run the notebook
   Open the Jupyter Notebook or VS Code and run all cells.

---

Example Interaction

User: “Add task – finish Tableau dashboard”
Bot: “Got it! Added ‘finish Tableau dashboard’ to your list.”

User: “Show all tasks.”
Bot: “Here’s your to-do list:
1️⃣ Finish Tableau dashboard
2️⃣ Update Power BI report”

---

Learning Takeaways

This project helped me understand how simple prompt tuning and memory context can make an AI system behave like a structured assistant.
It also showed how LLMs can replace traditional rule-based chatbots for task management, even with minimal code.

---

Future Enhancements

 Persistent storage (save tasks even after restarting)
 Due dates and priorities for tasks
 Voice-based task input
 Integration with Google Calendar or Notion

