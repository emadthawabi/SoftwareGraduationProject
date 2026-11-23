import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(".env")

with genai.Client(api_key=os.environ["GEMINI_API_KEY"]) as client:
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents="يستحق العامل أجراً مقابل عمله.",
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=1536,
        ),
    )

    vector = result.embeddings[0].values
    print("Connection successful")
    print("Vector dimensions:", len(vector))