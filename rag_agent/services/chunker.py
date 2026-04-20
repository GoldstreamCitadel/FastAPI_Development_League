from config import settings


def split_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + settings.CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - settings.CHUNK_OVERLAP
    return chunks