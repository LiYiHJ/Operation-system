from __future__ import annotations

from datetime import datetime
from typing import Any

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import inspect
from werkzeug.security import check_password_hash, generate_password_hash

from ecom_v51.config.settings import settings
from ecom_v51.db.models import ReminderReadState, UserAccount
from ecom_v51.db.session import get_engine, get_session


class AuthService:
    def __init__(self) -> None:
        self.signer = URLSafeTimedSerializer(settings.secret_key, salt='ecom_v51_auth')
        self._ensure_auth_tables()
        self._ensure_seed_users()

    @staticmethod
    def _ensure_auth_tables() -> None:
        engine = get_engine()
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        to_create = []
        if 'user_account' not in existing:
            to_create.append(UserAccount.__table__)
        if 'reminder_read_state' not in existing:
            to_create.append(ReminderReadState.__table__)
        if to_create:
            UserAccount.metadata.create_all(bind=engine, tables=to_create)

    @staticmethod
    def _ensure_seed_users() -> None:
        seeds = [
            ('operator', '运营专员', 'operator', '123456'),
            ('admin', '系统管理员', 'admin', 'admin123'),
            ('viewer', '只读观察员', 'viewer', 'viewer123'),
        ]
        with get_session() as session:
            for username, display_name, role, plain_password in seeds:
                user = session.query(UserAccount).filter(UserAccount.username == username).first()
                if not user:
                    session.add(UserAccount(
                        username=username,
                        display_name=display_name,
                        password_hash=generate_password_hash(plain_password),
                        role=role,
                        status='active',
                    ))

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        with get_session() as session:
            user = session.query(UserAccount).filter(UserAccount.username == username, UserAccount.status == 'active').first()
            if not user:
                return None
            if not check_password_hash(user.password_hash, password):
                return None
            return {
                'id': user.id,
                'username': user.username,
                'displayName': user.display_name,
                'role': user.role,
                'permissions': self.permissions_for_role(user.role),
                'status': user.status,
                'createdAt': user.created_at.isoformat() if user.created_at else None,
            }

    def issue_token(self, *, username: str) -> str:
        return self.signer.dumps({'username': username, 'ts': datetime.utcnow().isoformat()})

    def verify_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        try:
            payload = self.signer.loads(token, max_age=60 * 60 * 24)
        except (BadSignature, SignatureExpired):
            return None

        username = str(payload.get('username', ''))
        with get_session() as session:
            user = session.query(UserAccount).filter(UserAccount.username == username, UserAccount.status == 'active').first()
            if not user:
                return None
            return {
                'id': user.id,
                'username': user.username,
                'displayName': user.display_name,
                'role': user.role,
                'permissions': self.permissions_for_role(user.role),
                'status': user.status,
                'createdAt': user.created_at.isoformat() if user.created_at else None,
            }

    @staticmethod
    def permissions_for_role(role: str) -> list[str]:
        mapping = {
            'admin': ['view', 'operate', 'confirm', 'manage_users'],
            'operator': ['view', 'operate', 'confirm'],
            'viewer': ['view'],
        }
        return mapping.get(role, ['view'])
