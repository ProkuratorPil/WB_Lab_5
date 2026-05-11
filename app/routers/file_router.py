"""
Async router for file management with MinIO and MongoDB.
Supports multipart file upload, download, and delete operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from uuid import UUID
from typing import Optional

from app.core.dependencies import get_current_user
from app.models.user import UserDocument
from app.services.file_service import FileService
from app.schemas.file import FileResponse, PaginatedFileResponse
from app.schemas.common import get_auth_responses

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузка файла",
    description="Загружает файл в MinIO через multipart/form-data. Файл передаётся потоково. "
                "Максимальный размер: 10 MB. Доступно только для авторизованных пользователей.",
    response_description="Метаданные загруженного файла",
    responses={
        **get_auth_responses(401, 403, 422, 413),
        413: {"description": "Файл слишком большой (макс. 10 MB)"},
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def upload_file(
    file: UploadFile = File(..., description="Файл для загрузки"),
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Загрузка файла в MinIO.
    Доступ: Private (только авторизованные)
    
    Файл передаётся потоково (streaming) без полной буферизации в памяти.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Файл не предоставлен"
        )

    # Read file content for size validation
    file_content = await file.read()
    file_size = len(file_content)
    
    # Re-create a BytesIO stream from the content for MinIO streaming
    import io
    file_stream = io.BytesIO(file_content)
    
    service = FileService()
    
    try:
        file_doc = await service.upload_file(
            file_stream=file_stream,
            file_size=file_size,
            original_name=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            user_id=current_user.id,
        )
        return file_doc
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=PaginatedFileResponse,
    summary="Список файлов пользователя",
    description="Возвращает пагинированный список файлов текущего пользователя.",
    response_description="Пагинированный список метаданных файлов",
    responses={
        **get_auth_responses(401, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def list_user_files(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=100, description="Элементов на странице"),
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Получение списка файлов текущего пользователя (пагинированный).
    Доступ: Private (только авторизованные)
    """
    service = FileService()
    files, total = await service.get_user_files(current_user.id, page=page, limit=limit)
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return {
        "data": files,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": total_pages,
        }
    }


@router.get(
    "/{file_id}",
    summary="Скачивание файла",
    description="Скачивает файл по ID. Доступно только владельцу файла. "
                "Файл передаётся потоково через StreamingResponse.",
    response_description="Файл с правильными заголовками Content-Type, Content-Disposition, Content-Length",
    responses={
        **get_auth_responses(401, 403, 404),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def download_file(
    file_id: UUID,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Скачивание файла по ID.
    Доступ: Private (только владелец)
    
    Файл передаётся потоково (streaming) из MinIO.
    """
    service = FileService()
    stream, file_doc = await service.download_file_stream(file_id, current_user.id)

    if not file_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден"
        )

    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден в хранилище"
        )

    return StreamingResponse(
        content=stream.stream(32 * 1024),  # 32KB chunks
        media_type=file_doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_doc.original_name}"',
            "Content-Length": str(file_doc.size),
        }
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление файла",
    description="Удаляет файл (hard delete из MinIO + soft delete в MongoDB). "
                "Доступно только владельцу файла.",
    responses={
        **get_auth_responses(401, 403, 404),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def delete_file(
    file_id: UUID,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Удаление файла.
    Доступ: Private (только владелец)
    
    - Файл удаляется из MinIO (hard delete)
    - Метаданные помечаются как удалённые (soft delete) в MongoDB
    - Кеш метаданных инвалидируется
    """
    service = FileService()
    deleted = await service.delete_file(file_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден"
        )

    return None