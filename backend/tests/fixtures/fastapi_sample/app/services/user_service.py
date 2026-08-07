from app.repositories.user_repository import UserRepository

repository = UserRepository()


class UserService:
    def get_user(self, user_id: int):
        return repository.find_by_id(user_id)

    def create_user(self, name: str):
        return repository.create(name)
