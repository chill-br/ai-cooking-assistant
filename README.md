AI Cooking Assistant
This project is a voice-controlled AI Cooking Assistant designed to make your kitchen experience smoother and more interactive. Built with Flask for the backend and a responsive frontend using HTML, CSS, and JavaScript, it leverages advanced AI capabilities for natural language understanding and intelligent recipe guidance.

Key Features:

Voice Control: Interact with the assistant using voice commands to navigate recipes and get information.

Recipe Management: Browse a curated list of recipes, view detailed instructions and ingredients, and filter by categories (Vegetarian, Non-Vegetarian, Sweet).

Intelligent Assistance:

Natural Language Understanding (NLU) with SpaCy: Processes common cooking commands like "next step," "repeat step," "list ingredients," "how much [ingredient]," and "set timer."

Large Language Model (LLM) Integration (OpenAI API): For more complex or general cooking queries, the LLM provides intelligent and context-aware responses.

Dynamic Recipe Display: Instructions are presented step-by-step for easy following.

Database Integration (SQLite): Stores and manages recipe data efficiently.

User-Friendly Interface: A clean and intuitive web interface accessible from any device.

Technologies Used:

Backend: Python 3.10+, Flask

AI/NLP: SpaCy (en_core_web_sm model) for NLU, OpenAI API for LLM responses

Database: SQLite3

HTTP Client: httpx (configured to avoid proxy issues in deployment environments)

Frontend: HTML5, CSS3, JavaScript

Deployment: Designed for deployment on platforms like Render.com

How to Run Locally:

Clone the repository:

git clone https://github.com/chill-br/ai-cooking-assistant.git
cd ai-cooking-assistant

Set up a Python virtual environment:

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt
python -m spacy download en_core_web_sm

Set your OpenAI API Key:

export OPENAI_API_KEY="sk-YOUR_KEY_HERE" # macOS/Linux
# $env:OPENAI_API_KEY="sk-YOUR_KEY_HERE" # PowerShell (Windows)

Replace "sk-YOUR_KEY_HERE" with your actual OpenAI API key.

Run the Flask application:

python app.py

The application will typically run on http://127.0.0.1:5000.

Enjoy your AI-powered cooking journey!

Result:
![image](https://github.com/user-attachments/assets/0f1f2e21-64e9-4e15-a812-407bdb54942a)
![image](https://github.com/user-attachments/assets/14a2f0b0-e9a3-4f8d-bb16-daeeae74f700)
![image](https://github.com/user-attachments/assets/81e9c0dd-b1c2-4080-a45b-aa9570fcb746)

