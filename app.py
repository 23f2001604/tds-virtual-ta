from dotenv import load_dotenv
load_dotenv()

import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# Initialize OpenAI client with secure API key loading
client = OpenAI(api_key=os.environ.get("eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjIwMDE2MDRAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.fGCwu-15hgeDyOOqFOQ4HA5q0VILSBXrZZSCC4lBuyc"))

app = FastAPI()

# Enable CORS for all origins and methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Discourse posts
with open("discourse_posts.json", "r", encoding="utf-8") as f:
    discourse_posts = json.load(f)

# Load course markdown files
course_contents = []
tds_md_folder = "tds_pages_md"

for filename in os.listdir(tds_md_folder):
    if filename.endswith(".md"):
        with open(os.path.join(tds_md_folder, filename), "r", encoding="utf-8") as f:
            content = f.read()
            course_contents.append({
                "filename": filename,
                "content": content
            })

class QuestionRequest(BaseModel):
    question: str
    image: str = None

def search_all_sources(query, max_results=3):
    results = []

    # Search Discourse posts
    query_lower = query.lower()
    for post in discourse_posts:
        if query_lower in post["content"].lower():
            results.append({
                "source": "discourse",
                "url": post.get("post_url", ""),
                "text": post.get("content", "")[:100]
            })
        if len(results) >= max_results:
            break

    # If not enough results, search course markdowns
    if len(results) < max_results:
        for page in course_contents:
            if query_lower in page["content"].lower():
                results.append({
                    "source": "course",
                    "url": f"https://tds.s-anand.net/#{page['filename'].replace('.md','')}",
                    "text": page["content"][:100]
                })
            if len(results) >= max_results:
                break

    return results

@app.post("/api/")
async def answer_question(request: QuestionRequest):
    matches = search_all_sources(request.question)
    links = [{"url": match["url"], "text": match["text"]} for match in matches]
    context = "\n\n".join([match["text"] for match in matches])

    prompt = (
        f"Answer the following student question using the provided context from course discussions and course notes:\n"
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
