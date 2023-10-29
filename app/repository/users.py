from libgravatar import Gravatar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.model import User
from app.schemas import UserSchema,UserResponseSchema


async def get_user_by_email(email: str, db: AsyncSession) -> User:
    sq = select(User).filter(User.email == email)
    result = await db.execute(sq)
    user = result.scalar()
    return user

async def user_to_response_schema(user: User) -> UserResponseSchema:
    return UserResponseSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar=user.avatar
    )

async def create_user(body: UserSchema, db: AsyncSession) -> User:
    avatar = None
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as e:
        print(e)
    user_data = body.dict()
    new_user = User(**user_data, avatar=avatar)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_token(user: User, token: str | None, db: AsyncSession) -> None:
    user.refresh_token = token
    await db.commit()