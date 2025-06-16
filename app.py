from dotenv import load_dotenv
load_dotenv()




import json
import os
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from bs4 import BeautifulSoup

BASE_URL = "https://discourse.onlinedegree.iitm.ac.in"

# Initialize OpenAI client (uses OPENAI_API_KEY from your .env or environment)
client = OpenAI(
    api_key=os.environ.get("eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjIwMDE2MDRAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.fGCwu-15hgeDyOOqFOQ4HA5q0VILSBXrZZSCC4lBuyc")
)

app = FastAPI()

# Load all posts from all JSON files in discourse_json folder
discourse_posts = []
discourse_folder = Path("discourse_json")

for json_file in discourse_folder.glob("*.json"):
    with open(json_file, "r", encoding="utf-8") as f:
        topic_data = json.load(f)
        if "post_stream" in topic_data and "posts" in topic_data["post_stream"]:
            for post in topic_data["post_stream"]["posts"]:
                discourse_posts.append({
                    "username": post.get("username", ""),
                    "created_at": post.get("created_at", ""),
                    "content": BeautifulSoup(post.get("cooked", ""), "html.parser").get_text(),
                    "post_url": f"{BASE_URL}/t/{topic_data['id']}/{post['post_number']}"
                })

class QuestionRequest(BaseModel):
    question: str
    image: str = None

def search_posts(query, max_results=3):
    results = []
    query_lower = query.lower()
    for post in discourse_posts:
        if query_lower in post["content"].lower():
            results.append(post)
        if len(results) >= max_results:
            break
    return results

@app.post("/api/")
async def answer_question(request: QuestionRequest):
    matches = search_posts(request.question)
    links = [{"url": post["post_url"], "text": post["content"][:100]} for post in matches]
    context = "\n\n".join([post["content"] for post in matches])

    prompt = (
        f"Answer the following student question using the provided context from course discussions:\n"
        f"Question: {request.question}\n"
        f"Context:\n{context}\n"
        f"Give a clear, concise answer and cite any relevant links."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": prompt}],
            timeout=20
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Sorry, there was an error generating the answer: {e}"

    return {
        "answer": answer,
        "links": links
    }

