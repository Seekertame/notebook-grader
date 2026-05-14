from fastapi import HTTPException, UploadFile

MAX_UPLOAD_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


async def read_upload_with_limit(
    upload: UploadFile,
    max_size: int = MAX_UPLOAD_SIZE,
    chunk_size: int = CHUNK_SIZE,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            limit_mb = max_size // (1024 * 1024)
            filename = upload.filename or "<без имени>"
            raise HTTPException(
                status_code=413,
                detail=f"Файл превышает максимальный размер {limit_mb} МБ: {filename}",
            )
        chunks.append(chunk)
    return b"".join(chunks)
