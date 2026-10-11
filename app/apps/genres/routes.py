from fastapi import APIRouter, Depends, HTTPException, Response

from app.apps.genres.schemas import GenreCreateSchema, GenreSchema, GenreUpdateSchema
from app.apps.genres.services.service import GenreService
from app.core.exceptions import AlreadyExistError, NotFoundError

router = APIRouter(tags=['Genres'])


@router.get('/genres')
async def list_genres(service: GenreService = Depends()) -> list[GenreSchema]:
    genres = await service.list_genres()
    return genres


@router.get('/genres/{genre_id}')
async def get_genre_by_id(genre_id: int, service: GenreService = Depends()) -> GenreSchema:
    try:
        genre = await service.get_genre_by_id(genre_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return genre


@router.post('/genres', status_code=201)
async def create_genre(genre_creation: GenreCreateSchema, service: GenreService = Depends()) -> GenreSchema:
    genre = await service.create_genre(genre_creation)
    return genre


@router.put('/genres/{genre_id}')
async def update_genre(
    genre_id: int, genre_update: GenreUpdateSchema, service: GenreService = Depends()
) -> GenreSchema:
    try:
        genre = await service.update_genre(genre_update, genre_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except AlreadyExistError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return genre


@router.delete('/genres/{genre_id}', status_code=204, response_class=Response)
async def delete_genre(genre_id: int, service: GenreService = Depends()) -> None:
    try:
        await service.delete_genre(genre_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
