from app.apps.users.schemas import UserSchema
from tests.conftest import TestBaseClientDBClass
from tests.factory_models.factories import UserCreationFactory


class TestCreateUsers(TestBaseClientDBClass):
    async def test_success(self) -> None:
        user_fc = UserCreationFactory.build()
        response = await self.member_client.post('/users', json=user_fc.model_dump())

        assert response.status_code == 201
        assert UserSchema.model_validate(response.json()).model_dump(exclude={'id'}) == user_fc.model_dump()
