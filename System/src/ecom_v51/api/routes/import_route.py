"""
数据导入API路由
"""

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from pathlib import Path

import_bp = Blueprint('import', __name__)

# 上传目录
UPLOAD_FOLDER = Path(__file__).parent.parent.parent.parent / 'uploads'
UPLOAD_FOLDER.mkdir(exist_ok=True)


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
        
        # TODO: 调用ingestion.py解析文件
        
        result = {
            'fileName': filename,
            'filePath': str(filepath),
            'fileSize': os.path.getsize(filepath),
            'status': 'uploaded',
        }
        
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
        data = request.get_json()
        
        # TODO: 执行导入
        
        result = {
            'batchId': f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'status': 'success',
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
