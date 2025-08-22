from app.apps.consumers.schemas import UserCreationMsg, UserCreationStatus
from app.apps.users.schemas import UserSchema
from tests.conftest import TestBaseClientDBClass
from tests.factory_models.factories import UserCreationFactory


class TestCreateUsers(TestBaseClientDBClass):
    async def test_success(self, mock_broker) -> None:
        user_fc = UserCreationFactory.build()

        response = await self.member_client.post('/users', json=user_fc.model_dump())

        assert response.status_code == 201
        assert UserSchema.model_validate(response.json()).model_dump(exclude={'id'}) == user_fc.model_dump()
        msg = UserCreationMsg(username=user_fc.email, status=UserCreationStatus.SUCCESS)
        assert mock_broker.publish.call_args[0][0] == msg
