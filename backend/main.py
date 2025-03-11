import os
import json
import unicodedata
import scrapy
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from langchain_groq import ChatGroq
from langchain.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

# Load environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("🚨 GROQ_API_KEY is missing!")

# Initialize FastAPI
app = FastAPI()

# Initialize Llama 3 model
llm = ChatGroq(model_name="llama3-8b-8192", api_key=api_key)

# Initialize embeddings model
embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# === Scrapy Spider for Web Scraping === #
class ContentSpider(scrapy.Spider):
    name = "content"
    start_urls = ["https://www.csusb.edu/recreation-wellness"]
    def parse(self, response):
        for paragraph in response.css("p"):
            text = paragraph.get()
            clean_text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
            yield {"text": clean_text.strip()}

# Function to run Scrapy at startup
def run_scrapy_spider():
    settings = get_project_settings()
    settings.set("FEED_FORMAT", "json", priority=0)
    settings.set("FEED_URI", "scraped_data.json", priority=0)

    process = CrawlerProcess(settings)
    process.crawl(ContentSpider)
    process.start()

# Normalize and clean text
def normalize_text(text):
    text = text.lower().strip()
    return unicodedata.normalize("NFKC", text)

# Load and process scraped data
def load_scraped_data(file_path="scraped_data.json"):
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r") as file:
        data = json.load(file)

    cleaned_texts = [normalize_text(item["text"]) for item in data if len(item["text"].strip()) > 20]
    unique_texts = list(set(cleaned_texts))
    return [Document(page_content=text) for text in unique_texts]

# Run Scrapy at startup if no data exists
if not os.path.exists("scraped_data.json"):
    run_scrapy_spider()

# Create FAISS index
documents = load_scraped_data()
vectorstore = FAISS.from_documents(documents, embedding_function) if documents else None

# === API Models === #
class ChatRequest(BaseModel):
    profile: str
    message: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === FastAPI Endpoints === #
@app.post("/chat")
def chat(request: ChatRequest):
    if vectorstore is None:
        raise HTTPException(status_code=500, detail="No documents in FAISS yet. Try restarting the server.")

    retrieved_docs = vectorstore.similarity_search(request.message, k=3)
    context = "\n".join([doc.page_content for doc in retrieved_docs])

    prompt = f"Context:\n{context}\n\nUser: {request.message}"
    bot_response = llm.invoke(prompt).content.strip()

    return {"response": bot_response}

@app.get("/")
def home():
    return {"message": "FastAPI backend is running!"}
