import httpx
from redis import Redis
from sqlalchemy.orm import Session


class User:
    __tablename__ = "users"

    id: int
    name: str


class UserRepository:
    def find_by_id(self, user_id: int, db: Session, redis: Redis):
        cached = redis.get(f"user:{user_id}")
        if cached:
            return cached
        httpx.get("https://profiles.example.test/users")
        return db.get(User, user_id)

    def create(self, name: str, db: Session):
        user = User()
        user.name = name
        db.add(user)
        db.commit()
        return user
