from __future__ import annotations

import tempfile
import os
from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename

from ecom_v51.services import ImportCenterService

imports_bp = Blueprint("imports", __name__)
service = ImportCenterService()


@imports_bp.route("/imports", methods=["GET", "POST"])
def imports_index() -> str:
    """导入页面"""
    if request.method == "POST":
        uploaded = request.files.get("file")
        if uploaded and uploaded.filename:
            # 保存上传的文件到临时文件
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=os.path.splitext(uploaded.filename)[1]  # 保留原扩展名
            ) as tmp:
                uploaded.save(tmp.name)
                tmp_path = tmp.name
            
            try:
                # 使用临时文件路径
                result = service.import_from_file(tmp_path, save_to_db=False)
            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        else:
            # 无文件，返回空结果
            result = {
                "success": False,
                "total_rows": 0,
                "imported": 0,
                "failed": 0,
                "data": [],
                "errors": [],
                "warnings": [],
            }
    else:
        # GET 请求，显示空状态
        result = {
            "success": None,
            "total_rows": 0,
            "imported": 0,
            "failed": 0,
            "data": [],
            "errors": [],
            "warnings": [],
        }

    batches = service.list_batches()
    return render_template("imports/index.html", preview=result, batches=batches)


@imports_bp.route("/api/import", methods=["POST"])
def api_import():
    """API 接口：导入文件"""
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "未选择文件"}), 400
    
    # API 接口同样需要保存到临时文件
    with tempfile.NamedTemporaryFile(
        delete=False, 
        suffix=os.path.splitext(uploaded.filename)[1]
    ) as tmp:
        uploaded.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        result = service.import_from_file(tmp_path, save_to_db=False)
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass
    
    return jsonify(result)