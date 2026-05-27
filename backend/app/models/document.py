import uuid
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """Represents one piece of text extracted from a larger document."""

    content: str           # The actual text
    source_filename: str   # Original uploaded filename (e.g. "report.pdf")
    page_number: int = 0   # 1-indexed page number (0 for text files without pages)
    chunk_index: int = 0   # Sequential position within the document

    # tenant_id isolates data between organisations — all queries filter by this value
    # Defaults to "default" so existing single-tenant usage is unchanged
    tenant_id: str = "default"

    # Auto-generate a unique ID so Pinecone and ES always reference the same chunk
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict = field(default_factory=dict)
