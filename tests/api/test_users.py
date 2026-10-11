from unittest.mock import AsyncMock

from app.apps.consumers.schemas import UserCreationMessage, UserCreationStatus
from app.apps.users.schemas import UserSchema
from tests.conftest import TestBaseClientDBClass
from tests.factory_models.factories import UserCreationFactory


class TestCreateUsers(TestBaseClientDBClass):
    async def test_user_registered(self, mock_broker: AsyncMock) -> None:
        user_creation = UserCreationFactory.build()

        response = await self.member_client.post('/users', json=user_creation.model_dump())

        assert response.status_code == 201
        assert UserSchema.model_validate(response.json()).model_dump(exclude={'id'}) == user_creation.model_dump()
        expected_message = UserCreationMessage(username=user_creation.email, status=UserCreationStatus.SUCCESS)
        assert mock_broker.publish.call_args[0][0] == expected_message
