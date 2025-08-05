from passlib.context import CryptContext
from . import models, schemas

# Şifreleme için context oluştur
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_user_by_api_key(api_key: str) -> models.User | None:
    """API anahtarına göre kullanıcıyı bulur."""
    return await models.User.find_one(models.User.api_key == api_key)

async def get_user_by_email(email: str) -> models.User | None:
    """Email adresine göre kullanıcıyı bulur."""
    return await models.User.find_one(models.User.email == email)

async def create_user(user: schemas.UserCreate) -> models.User:
    """Yeni bir kullanıcı oluşturur, şifresini hashler ve veritabanına ekler."""
    hashed_password = pwd_context.hash(user.password)
    # Not: API anahtarı, models.py'deki default_factory sayesinde otomatik oluşturulur.
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password
    )
    await db_user.insert()
    return db_user

async def increment_search_count(user_id) -> models.User | None:
    """Kullanıcının arama sayacını bir artırır."""
    db_user = await models.User.get(user_id)
    if db_user:
        db_user.search_count += 1
        await db_user.save()
    return db_user