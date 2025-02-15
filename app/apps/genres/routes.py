from fastapi import APIRouter, Depends, HTTPException

from app.apps.genres.schemas import GenreCreateUpdate, GenreSchema
from app.apps.genres.services.service import GenreService
from app.core.exceptions import AlreadyExistError, NotFoundError

router = APIRouter(tags=['Genres'])


@router.get('/genres')
async def list_genres(service: GenreService = Depends()) -> list[GenreSchema]:
    genres = await service.get_all_genres()
    return genres


@router.get('/genres/{genre_id}')
async def get_by_id(genre_id: int, service: GenreService = Depends()) -> GenreSchema:
    try:
        genre = await service.get_genre_by_id(genre_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return genre


@router.post('/genres', status_code=201)
async def create_genre(genre: GenreCreateUpdate, service: GenreService = Depends()) -> GenreSchema:
    genres = await service.create_genre(genre)
    return genres


@router.put('/genres/{genre_id}')
async def update_genre(genre_id: int, genre_input: GenreCreateUpdate, service: GenreService = Depends()) -> GenreSchema:
    try:
        genre = await service.update_genre(genre_input, genre_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AlreadyExistError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return genre


@router.delete('/genres/{genre_id}', status_code=204)
async def delete_genre(genre_id: int, service: GenreService = Depends()):
    try:
        await service.delete_genre(genre_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
