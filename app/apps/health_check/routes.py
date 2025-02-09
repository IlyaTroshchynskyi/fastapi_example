from fastapi import APIRouter, Response

router = APIRouter(tags=['Health Check'])


@router.get('/health-check', status_code=204, response_class=Response)
async def check_service_running() -> None:
    return None
