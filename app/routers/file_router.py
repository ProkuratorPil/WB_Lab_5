"""
Async router for file management with MongoDB.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from uuid import UUID
from typing import Optional

from app.core.dependencies import get_current_user
from app.models.user import UserDocument
from app.services.file_service import FileService
from app.schemas.file import FileCreate, FileUpdate, FileResponse, PaginationParams, PaginatedResponse
from app.schemas.common import get_auth_responses

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание записи о файле",
    description="Создаёт новую запись о файле для текущего авторизованного пользователя.",
    response_description="Данные созданной записи о файле",
    responses={
        **get_auth_responses(400, 401, 403, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def create_file(
    file_data: FileCreate,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Создание записи о файле.
    Доступ: Private (только авторизованные)
    """
    if str(file_data.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя создавать файлы для других пользователей"
        )

    service = FileService()
    file_entry = await service.create(file_data)
    return file_entry


@router.get(
    "/",
    response_model=PaginatedResponse,
    summary="Получение списка файлов",
    description="Возвращает пагинированный список файлов текущего авторизованного пользователя.",
    response_description="Пагинированный список файлов",
    responses={
        **get_auth_responses(401, 403, 404, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def get_files(
    pagination: PaginationParams = Depends(),
    user_id_filter: Optional[UUID] = None,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Получение списка файлов (пагинированный).
    Доступ: Private

    Пользователь видит только свои файлы.
    """
    user_filter = current_user.id

    service = FileService()
    files, total, total_pages = await service.get_all_active(
        pagination,
        user_id_filter=user_filter
    )
    return {
        "data": files,
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages,
        }
    }


@router.get(
    "/{file_id}",
    response_model=FileResponse,
    summary="Получение файла по ID",
    description="Возвращает данные файла по указанному ID. Доступ только для владельца файла.",
    response_description="Данные файла",
    responses={
        **get_auth_responses(401, 403, 404),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def get_file(
    file_id: UUID,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Получение файла по ID.
    Доступ: Private (только владелец)
    """
    service = FileService()
    file_entry = await service.get_by_id(file_id)

    if not file_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if file_entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на просмотр этого файла"
        )

    return file_entry


@router.put(
    "/{file_id}",
    response_model=FileResponse,
    summary="Полное обновление записи о файле",
    description="Обновляет все поля записи о файле (PUT). Доступ только для владельца файла.",
    response_description="Данные обновленной записи о файле",
    responses={
        **get_auth_responses(401, 403, 404, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def update_file_full(
    file_id: UUID,
    file_data: FileUpdate,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Полное обновление записи о файле.
    Доступ: Private (только владелец)
    """
    service = FileService()
    existing = await service.get_by_id(file_id)

    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование этого файла"
        )

    file_entry = await service.update(file_id, file_data)
    return file_entry


@router.patch(
    "/{file_id}",
    response_model=FileResponse,
    summary="Частичное обновление записи о файле",
    description="Обновляет указанные поля записи о файле (PATCH). Доступ только для владельца файла.",
    response_description="Данные обновленной записи о файле",
    responses={
        **get_auth_responses(401, 403, 404, 422),
    },
    openapi_extra={"security": [{"bearerAuth": []}, {"cookieAuth": []}]}
)
async def update_file_partial(
    file_id: UUID,
    file_data: FileUpdate,
    current_user: UserDocument = Depends(get_current_user)
):
    """
    Частичное обновление записи о файле.
    Доступ: Private (только владелец)
    """
    service = FileService()
    existing = await service.get_by_id(file_id)

    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на редактирование этого файла"
        )

    file_entry = await service.update(file_id, file_data)
    return file_entry


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление файла (Soft Delete)",
    description="Помечает файл как удаленного (Soft Delete). Доступ только для владельца файла.",
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
    Удаление файла (Soft Delete).
    Доступ: Private (только владелец)
    """
    service = FileService()
    existing = await service.get_by_id(file_id)

    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if existing.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав на удаление этого файла"
        )

    deleted = await service.delete(file_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return None