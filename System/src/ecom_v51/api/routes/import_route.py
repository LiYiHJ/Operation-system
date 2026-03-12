"""
数据导入API路由
"""

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path

from ecom_v51.services.import_service import ImportService

import_bp = Blueprint('import', __name__)

# 上传目录
UPLOAD_FOLDER = Path(__file__).parent.parent.parent.parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)
import_service = ImportService()


@import_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    上传文件
    前端调用: importAPI.uploadFile(file)
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': '未找到文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_with_ts = f"{timestamp}_{filename}"
        filepath = UPLOAD_FOLDER / filename_with_ts
        file.save(filepath)
        
        shop_id = int(request.form.get('shop_id') or 1)
        operator = request.form.get('operator') or 'frontend_user'
        result = import_service.parse_import_file(str(filepath), shop_id=shop_id, operator=operator)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@import_bp.route('/confirm', methods=['POST'])
def confirm_import():
    """
    确认导入
    前端调用: importAPI.confirmImport(data)
    """
    try:
        data = request.get_json() or {}
        result = import_service.confirm_import(
            session_id=int(data.get('sessionId') or 0),
            shop_id=int(data.get('shopId') or 1),
            manual_overrides=data.get('manualOverrides') or [],
            operator=data.get('operator') or 'frontend_user',
        )
        result['success'] = result.get('status') == 'success'
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
