from app import db, login_manager
from app.models.models import User

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
