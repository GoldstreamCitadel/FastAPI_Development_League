# use local SentenceTransformer for embedding
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer(
    r"D:\sexy_python\models\sentence-transformers\all-MiniLM-L6-v2"
)

async def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


# --- OpenAI API 版本（备用，需要兼容 OpenAI 接口的 key）---
# from openai import AsyncOpenAI
# from config import settings
#
# _client = AsyncOpenAI(
#     api_key=settings.OPENAI_API_KEY,
#     base_url=settings.OPENAI_API_BASE,
# )
#
# async def embed_texts(texts: list[str]) -> list[list[float]]:
#     response = await _client.embeddings.create(
#         model=settings.EMBEDDING_MODEL,
#         input=texts,
#     )
#     return [item.embedding for item in response.data]
