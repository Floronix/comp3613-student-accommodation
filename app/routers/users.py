from app.dependencies import SessionDep
from app.dependencies.auth import AdminDep
from app.repositories.user import UserRepository
from app.schemas import UserResponse
from app.services.user_service import UserService
from . import api_router


@api_router.get("/users", response_model=list[UserResponse])
async def list_users(db: SessionDep, admin: AdminDep):
    """List users for admins only."""
    user_repo = UserRepository(db)
    user_service = UserService(user_repo)
    return user_service.get_all_users()
