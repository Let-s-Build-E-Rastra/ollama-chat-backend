from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query

from app.db.mongodb import mongodb
from app.db.qdrant import qdrant_db
from app.models.agent import Agent
from app.models.file import File as FileModel, FileCreate, FileResponse
from app.rag.preprocessor import TextPreprocessor
from app.rag.chunker import TextChunker
from app.rag.embedder import embedder
from app.core.config import settings

router = APIRouter()
preprocessor = TextPreprocessor()


@router.post("/upload", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...),
    agent_id: str = Form(...),
    current_agent: Agent = Depends(None)
):
    """Upload and index a file for RAG"""
    # Verify agent exists and matches current agent
    agent = await mongodb.get_active_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found or inactive"
        )

    # Check file size
    content = await file.read()
    if len(content) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size} bytes"
        )

    # Create file record in MongoDB
    file_record = await mongodb.create_file(
        FileCreate(
            agent_id=agent_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size=len(content)
        )
    )

    try:
        # Preprocess file content
        text_content = preprocessor.preprocess_file_content(
            content,
            file.filename
        )

        # Create chunker and generate chunks
        chunker = TextChunker(
            chunk_size=settings.default_chunk_size,
            chunk_overlap=settings.default_chunk_overlap
        )
        chunks = chunker.semantic_chunk(text_content, source=file.filename)
        chunk_contents = [chunk.content for chunk in chunks]

        # Generate embeddings
        embeddings = await embedder.get_embeddings_batch(
            chunk_contents,
            agent.embedding_model
        )

        # Filter out failed embeddings
        valid_chunks = []
        valid_embeddings = []
        valid_payloads = []

        for chunk, embedding in zip(chunks, embeddings):
            if embedding:
                valid_chunks.append(chunk)
                valid_embeddings.append(embedding)
                valid_payloads.append({
                    "section": chunk.section or "",
                    "source": chunk.source or file.filename
                })

        if not valid_embeddings:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate embeddings for any chunks"
            )

        # Store vectors in Qdrant
        success = await qdrant_db.upsert_vectors(
            agent_id=agent_id,
            file_id=str(file_record.id),
            vectors=valid_embeddings,
            payloads=valid_payloads,
            chunk_indices=list(range(len(valid_chunks)))
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to store vectors in Qdrant"
            )

        # Update file record with chunk count
        await mongodb.update_file_chunk_count(str(file_record.id), len(valid_chunks))

        return {
            "message": "File uploaded and indexed successfully",
            "file_id": str(file_record.id),
            "filename": file.filename,
            "chunks_created": len(valid_chunks),
            "agent_id": agent_id
        }

    except Exception as e:
        # Rollback on error
        await mongodb.mark_file_deleted(str(file_record.id))
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/", response_model=List[FileResponse])
async def list_files(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    include_deleted: bool = Query(False, description="Include deleted files"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_agent: Agent = Depends(None)
):
    """List files"""
    if agent_id:
        agent = await mongodb.get_active_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=404,
                detail="Agent not found or inactive"
            )
        files = await mongodb.list_files_by_agent(agent_id, include_deleted)
    else:
        files = await mongodb.list_files_by_agent(str(current_agent.id), include_deleted)

    return [FileResponse(**file.model_dump()) for file in files]


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_agent: Agent = Depends(None)
):
    """Get file by ID"""
    file_record: FileModel = await mongodb.get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if str(current_agent.id) != file_record.agent_id:
        raise HTTPException(status_code=403, detail="Access denied to this file")

    return FileResponse(**file_record.model_dump())


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_agent: Agent = Depends(None)
):
    """Soft delete a file and remove vectors from Qdrant"""
    file_record: FileModel = await mongodb.get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if str(current_agent.id) != file_record.agent_id:
        raise HTTPException(status_code=403, detail="Access denied to this file")

    success = await qdrant_db.delete_vectors_by_file(
        agent_id=str(current_agent.id),
        file_id=file_id
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete vectors from Qdrant")

    await mongodb.mark_file_deleted(file_id)

    return {
        "message": "File deleted successfully",
        "file_id": file_id,
        "vectors_removed": True
    }


@router.get("/{file_id}/chunks")
async def get_file_chunks(
    file_id: str,
    current_agent: Agent = Depends(None)
):
    """Get chunk information for a file"""
    file_record: FileModel = await mongodb.get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    if str(current_agent.id) != file_record.agent_id:
        raise HTTPException(status_code=403, detail="Access denied to this file")

    vector_count = await qdrant_db.count_vectors_by_file(
        agent_id=str(current_agent.id),
        file_id=file_id
    )

    return {
        "file_id": file_id,
        "filename": file_record.filename,
        "chunk_count": file_record.chunk_count,
        "vector_count": vector_count,
        "agent_id": file_record.agent_id
    }
