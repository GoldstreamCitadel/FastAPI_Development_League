# ChromaDB sealing
# 实际处理调用在process里，这里只做封装
import chromadb

from config import settings

_client = chromadb.PersistentClient(
    path=settings.CHROMA_PATH
)
# 模块级单例，程序启动时创建一次，向量数据持久化到磁盘（不是内存库）。


def get_collection(name: str = "documents") -> chromadb.Collection:
    return _client.get_or_create_collection(name)
    # 有则取，无则建


def upsert(
        collection: chromadb.Collection,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
) -> None:
    # 有则更新，无则插入
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents
    )


def query(
        collection: chromadb.Collection,
        embedding: list[float],
        n_results: int = 5,
) -> dict:
    # 入一个查询向量，返回最相似的n条结果（含文本、距离等）。
    # 注意入参要包在列表里[embedding]，这是 ChromaDB 的约定。
    return collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )


def delete(
        collection: chromadb.Collection,
        ids: list[str]
) -> None:
    # 按id精确删掉某篇文档全部块
    collection.delete(ids=ids)