# Samsung Phone Query and Review System

An AI assistant that answers questions about Samsung phones and writes phone reviews.
I built this project for the GTR AI internship assessment.

## What It Does

- **Answers questions** about 15 Samsung phones, for example:
  "Which phone has the best battery life?" or "Compare the Galaxy S23 and S24."
- **Writes phone reviews** using two AI agents. One agent finds the phone's specs,
  and the other agent writes the review.
- **Works through an API**, so any app can use it.

Everything runs on my own computer. No paid services are needed.

## Tech Stack

| Part | Tool |
|---|---|
| Web scraping | Requests, BeautifulSoup |
| Database | MySQL |
| Language model | Qwen2.5-3B-Instruct (Hugging Face), run with Ollama |
| Search | Chroma, sentence-transformers (all-MiniLM-L6-v2) |
| Chatbot logic | LangChain |
| AI agents | CrewAI |
| API | FastAPI |
| Testing | Postman |

## Project Structure

```
scraper/     Collects phone data from GSMArena
database/    Cleans the data and saves it in MySQL
chatbot/     The question-answering chatbot (RAG)
agents/      The two AI agents that write reviews
api/         The FastAPI server
postman/     Postman collection for testing
data/        The collected phone data (phones.json)
Modelfile    Settings for the language model
```

## How It Works

1. **Collect the data.** The scraper downloads 15 phone pages from GSMArena. It saves
   each page, so it only downloads it once, and waits a few seconds between requests.
2. **Store the data.** The data is cleaned and saved in MySQL in three tables:
   phones, specifications and prices.
3. **Answer questions.** The chatbot first finds which phones the question is about.
   Then it pulls only the data for those phones and gives it to the language model,
   which writes the answer. This way, the answers come from real data.
4. **Write reviews.** The first agent gets the phone's specs from the database.
   The second agent uses those specs to write a review with eight sections and a
   score out of 10.

## Setup

You need Python 3.11 or newer, MySQL 8 and [Ollama](https://ollama.com).

**Step 1: Install the packages**
```bash
python -m venv env
source env/Scripts/activate
pip install -r requirements.txt
```

**Step 2: Create the database**

Run this in MySQL:
```sql
CREATE DATABASE samsung_phones CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'samsung_app'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON samsung_phones.* TO 'samsung_app'@'localhost';
```
Then copy `.env.example`, rename it to `.env`, and add your password.

**Step 3: Download the model**
```bash
ollama pull hf.co/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M
ollama create qwen2.5-3b -f Modelfile
```

**Step 4: Prepare the data**
```bash
python -m scraper.run_scraper
python -m database.load_data
python -m chatbot.vector_store
```

**Step 5: Start the server**
```bash
uvicorn api.main:app --port 8001
```
Now open http://127.0.0.1:8001/docs in your browser to try it.
You can also import the file in the `postman/` folder into the Postman desktop app.

## API Endpoints

| Method | Endpoint | Description | Example body |
|---|---|---|---|
| GET | `/` | Shows basic API info | |
| GET | `/phones` | Lists all phones | |
| POST | `/chat` | Answers a question | `{"question": "Which phone has the best camera?"}` |
| POST | `/review` | Writes a phone review | `{"phone": "Galaxy S24 Ultra"}` |

If the phone is not in the database, `/review` returns a 404 error.

## Challenges I Solved

- **Wrong phone in the answer.** At first, a question about the S23 also returned data
  about the S23 FE. I fixed this by finding the phone names in the question first and
  then searching each phone's data separately.
- **Wrong data on the website.** GSMArena showed a wrong US price for the Galaxy A55.
  I added a check that removes prices that don't make sense.
- **Mistakes in the reviews.** The small model sometimes mixed up lines, for example
  writing "No NFC" when the phone has NFC. I fixed this by sending the agent only the
  specs it needs. This also made reviews faster.

## Limitations

- The model is small, so reviews can still have small mistakes.
- A review takes about 2 to 3 minutes because everything runs on a CPU.
- The data covers 15 phones and was collected in November 2026.
  Prices do not update automatically.

## Data Source

All phone data comes from [GSMArena](https://www.gsmarena.com) and was collected
only for this assessment.