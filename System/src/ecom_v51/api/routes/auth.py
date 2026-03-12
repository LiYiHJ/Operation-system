"""轻量认证 API"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ecom_v51.services.auth_service import AuthService


auth_bp = Blueprint('auth', __name__)

_REVOKED: set[str] = set()
_service = AuthService()


def _extract_token() -> str | None:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth.replace('Bearer ', '').strip()
    return None


@auth_bp.route('/login', methods=['POST'])
def login():
    payload = request.get_json() or {}
    username = str(payload.get('username', '')).strip()
    password = str(payload.get('password', '')).strip()
    if not username or not password:
        return jsonify({'error': '用户名或密码不能为空'}), 400

    user_payload = _service.authenticate(username=username, password=password)
    if not user_payload:
        return jsonify({'error': '用户名或密码错误，或账号已停用'}), 401

    token = _service.issue_token(username=username)
    return jsonify({'token': token, 'user': user_payload})


@auth_bp.route('/me', methods=['GET'])
def me():
    token = _extract_token()
    if token in _REVOKED:
        return jsonify({'authenticated': False}), 401

    user = _service.verify_token(token)
    if not user:
        return jsonify({'authenticated': False}), 401

    return jsonify({'authenticated': True, 'user': user})


@auth_bp.route('/logout', methods=['POST'])
def logout():
    token = _extract_token()
    if token:
        _REVOKED.add(token)
    return jsonify({'status': 'success'})
