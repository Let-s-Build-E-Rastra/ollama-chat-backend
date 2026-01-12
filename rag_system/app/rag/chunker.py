import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import tiktoken


@dataclass
class Chunk:
    content: str
    chunk_index: int
    section: Optional[str] = None
    source: Optional[str] = None
    token_count: Optional[int] = None


class TextChunker:
    """Semantic text chunking for RAG pipeline"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def split_by_headers(self, text: str) -> List[Dict[str, Any]]:
        """Split text by section headers"""
        sections = []
        current_section = None
        current_content = []
        
        lines = text.split('\n')
        
        for line in lines:
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_content:
                    sections.append({
                        "section": current_section,
                        "content": '\n'.join(current_content)
                    })
                
                # Start new section
                current_section = header_match.group(2)
                current_content = [line]
            else:
                current_content.append(line)
        
        # Don't forget the last section
        if current_content:
            sections.append({
                "section": current_section,
                "content": '\n'.join(current_content)
            })
        
        return sections
    
    def split_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs"""
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean up paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences"""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def create_chunk(
        self,
        content: str,
        chunk_index: int,
        section: Optional[str] = None,
        source: Optional[str] = None
    ) -> Chunk:
        """Create a chunk with metadata"""
        token_count = self.count_tokens(content)
        return Chunk(
            content=content,
            chunk_index=chunk_index,
            section=section,
            source=source,
            token_count=token_count
        )
    
    def chunk_by_size(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        section: Optional[str] = None,
        source: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk text by token size with overlap"""
        tokens = self.encoding.encode(text)
        chunks = []
        chunk_index = 0
        
        start = 0
        while start < len(tokens):
            # Calculate end position
            end = min(start + chunk_size, len(tokens))
            
            # Decode chunk
            chunk_tokens = tokens[start:end]
            chunk_content = self.encoding.decode(chunk_tokens)
            
            # Create chunk
            chunk = self.create_chunk(
                content=chunk_content,
                chunk_index=chunk_index,
                section=section,
                source=source
            )
            chunks.append(chunk)
            chunk_index += 1
            
            # Move to next chunk with overlap
            if end >= len(tokens):
                break
            start = end - overlap
        
        return chunks
    
    def semantic_chunk(
        self,
        text: str,
        source: Optional[str] = None
    ) -> List[Chunk]:
        """Create semantic chunks respecting document structure"""
        chunks = []
        chunk_index = 0
        
        # First, try to split by sections
        sections = self.split_by_headers(text)
        
        if len(sections) > 1:
            # Process each section
            for section_data in sections:
                section_name = section_data["section"]
                section_content = section_data["content"]
                
                # If section is small enough, use as single chunk
                if self.count_tokens(section_content) <= self.chunk_size:
                    chunk = self.create_chunk(
                        content=section_content,
                        chunk_index=chunk_index,
                        section=section_name,
                        source=source
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                else:
                    # Split section by paragraphs
                    paragraphs = self.split_by_paragraphs(section_content)
                    current_chunk = ""
                    
                    for para in paragraphs:
                        # Check if adding this paragraph would exceed chunk size
                        combined = current_chunk + "\n\n" + para if current_chunk else para
                        
                        if self.count_tokens(combined) > self.chunk_size:
                            # Save current chunk if it exists
                            if current_chunk:
                                chunk = self.create_chunk(
                                    content=current_chunk,
                                    chunk_index=chunk_index,
                                    section=section_name,
                                    source=source
                                )
                                chunks.append(chunk)
                                chunk_index += 1
                            
                            # Start new chunk with current paragraph
                            current_chunk = para
                        else:
                            current_chunk = combined
                    
                    # Don't forget the last chunk in this section
                    if current_chunk:
                        chunk = self.create_chunk(
                            content=current_chunk,
                            chunk_index=chunk_index,
                            section=section_name,
                            source=source
                        )
                        chunks.append(chunk)
                        chunk_index += 1
        else:
            # No sections found, chunk the entire text
            return self.chunk_by_size(
                text,
                self.chunk_size,
                self.chunk_overlap,
                section=None,
                source=source
            )
        
        # Handle overlap between chunks if needed
        if len(chunks) > 1 and self.chunk_overlap > 0:
            chunks = self._apply_overlap(chunks)
        
        return chunks
    
    def _apply_overlap(self, chunks: List[Chunk]) -> List[Chunk]:
        """Apply overlap between chunks"""
        # For simplicity, we'll just return the chunks as-is
        # In a production system, you'd implement sophisticated overlap logic
        return chunks
    
    def merge_small_chunks(self, chunks: List[Chunk], min_size: int = 50) -> List[Chunk]:
        """Merge small chunks to meet minimum size requirements"""
        if len(chunks) <= 1:
            return chunks
        
        merged_chunks = []
        current_chunk = chunks[0]
        
        for next_chunk in chunks[1:]:
            combined_content = current_chunk.content + "\n\n" + next_chunk.content
            combined_tokens = self.count_tokens(combined_content)
            
            # If current chunk is too small or combined is still reasonable
            if (current_chunk.token_count < min_size and 
                combined_tokens <= self.chunk_size):
                # Merge chunks
                current_chunk.content = combined_content
                current_chunk.token_count = combined_tokens
            else:
                # Save current chunk and start new one
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        
        # Don't forget the last chunk
        merged_chunks.append(current_chunk)
        
        return merged_chunks