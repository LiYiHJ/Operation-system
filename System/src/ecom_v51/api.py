#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 FastAPI 后端服务
提供完整的 REST API 接口
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import json
import tempfile
from pathlib import Path
import logging

from .models import SkuSnapshot, ProfitInput
from .profit_solver import ProfitSolver
from .strategy import StrategyEngine
from .war_room import WarRoomService
from .data_importer import DataImporter, ImportResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="V5.1 跨境电商智能运营系统",
    description="智能 SKU 运营分析和策略推荐系统",
    version="5.1.0",
)

# CORS 配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
profit_solver = ProfitSolver()
strategy_engine = StrategyEngine()
war_room_service = WarRoomService()
data_importer = DataImporter()


# ==================== API 数据模型 ====================

class HealthResponse(BaseModel):
    status: str
    version: str
    modules: Dict[str, bool]


class WarRoomRequest(BaseModel):
    sku_data: Dict


class ProfitCalculationRequest(BaseModel):
    sale_price: float
    list_price: float
    variable_rate_total: float
    fixed_cost_total: float
    discount_ratios: Optional[List[float]] = [0.95, 0.9, 0.85]


class TargetProfitRequest(BaseModel):
    target_profit: Optional[float] = None
    target_margin: Optional[float] = None
    target_roi: Optional[float] = None
    variable_rate_total: float
    fixed_cost_total: float


# ==================== 健康检查 ====================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """系统健康检查"""
    try:
        # 测试各模块
        modules = {
            "profit_solver": True,
            "strategy_engine": True,
            "war_room_service": True,
            "data_importer": True,
        }
        
        # 测试利润求解器
        test_input = ProfitInput(
            sale_price=100,
            list_price=120,
            variable_rate_total=0.35,
            fixed_cost_total=80,
        )
        profit_solver.solve_current(test_input)
        
        return {
            "status": "healthy",
            "version": "5.1.0",
            "modules": modules,
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据导入 API ====================

@app.post("/api/import/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件并导入数据"""
    try:
        # 保存临时文件
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        # 导入数据
        result = data_importer.import_from_file(tmp_path)
        
        # 清理临时文件
        Path(tmp_path).unlink()
        
        return JSONResponse(content=result.to_dict())
    
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/preview")
async def preview_file(file: UploadFile = File(...), rows: int = 10):
    """预览文件前 N 行"""
    try:
        # 保存临时文件
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        # 读取文件
        df = data_importer._read_file(Path(tmp_path))
        
        # 清理临时文件
        Path(tmp_path).unlink()
        
        # 返回前 N 行
        preview_data = df.head(rows).to_dict(orient='records')
        
        return {
            "total_rows": len(df),
            "preview_rows": len(preview_data),
            "columns": df.columns.tolist(),
            "data": preview_data,
        }
    
    except Exception as e:
        logger.error(f"文件预览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 作战室 API ====================

@app.post("/api/war-room/analyze")
async def analyze_sku(request: WarRoomRequest):
    """分析单个 SKU 并生成作战室报告"""
    try:
        # 构建 SKU 快照
        snapshot = SkuSnapshot(**request.sku_data)
        
        # 生成报告
        report = war_room_service.build_report(snapshot)
        
        # 转换为字典
        from dataclasses import asdict
        return JSONResponse(content=asdict(report))
    
    except Exception as e:
        logger.error(f"作战室分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/war-room/batch-analyze")
async def batch_analyze_skus(sku_list: List[Dict]):
    """批量分析 SKU"""
    try:
        results = []
        for sku_data in sku_list:
            snapshot = SkuSnapshot(**sku_data)
            report = war_room_service.build_report(snapshot)
            
            from dataclasses import asdict
            results.append(asdict(report))
        
        return {
            "total": len(results),
            "results": results,
        }
    
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 利润求解器 API ====================

@app.post("/api/profit/calculate")
async def calculate_profit(request: ProfitCalculationRequest):
    """计算利润"""
    try:
        input_data = ProfitInput(
            sale_price=request.sale_price,
            list_price=request.list_price,
            variable_rate_total=request.variable_rate_total,
            fixed_cost_total=request.fixed_cost_total,
        )
        
        # 当前利润
        current_profit = profit_solver.solve_current(input_data)
        
        # 折扣模拟
        discount_simulations = profit_solver.simulate_discounts(
            input_data, request.discount_ratios
        )
        
        from dataclasses import asdict
        return {
            "current_profit": asdict(current_profit),
            "discount_simulations": [asdict(sim) for sim in discount_simulations],
        }
    
    except Exception as e:
        logger.error(f"利润计算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profit/target-price")
async def calculate_target_price(request: TargetProfitRequest):
    """反推目标价格"""
    try:
        results = {}
        
        if request.target_profit is not None:
            price = profit_solver.target_profit_price(
                request.target_profit,
                request.variable_rate_total,
                request.fixed_cost_total,
            )
            results["target_profit_price"] = price
        
        if request.target_margin is not None:
            price = profit_solver.target_margin_price(
                request.target_margin,
                request.variable_rate_total,
                request.fixed_cost_total,
            )
            results["target_margin_price"] = price
        
        if request.target_roi is not None:
            price = profit_solver.target_roi_price(
                request.target_roi,
                request.variable_rate_total,
                request.fixed_cost_total,
            )
            results["target_roi_price"] = price
        
        return results
    
    except Exception as e:
        logger.error(f"目标价格计算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 策略引擎 API ====================

@app.post("/api/strategy/generate")
async def generate_strategies(metrics: Dict):
    """生成策略任务"""
    try:
        tasks = strategy_engine.generate_for_sku(**metrics)
        
        from dataclasses import asdict
        return {
            "total": len(tasks),
            "tasks": [asdict(task) for task in tasks],
        }
    
    except Exception as e:
        logger.error(f"策略生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统诊断 API ====================

@app.get("/api/system/diagnostics")
async def run_diagnostics():
    """运行系统诊断"""
    try:
        from .system_diagnostics import main as run_diag
        import io
        import sys
        
        # 捕获输出
        old_stdout = sys.stdout
        sys.stdout = mystdout = io.StringIO()
        
        run_diag()
        
        sys.stdout = old_stdout
        output = mystdout.getvalue()
        
        return {
            "status": "success",
            "output": output,
        }
    
    except Exception as e:
        logger.error(f"系统诊断失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 启动服务器 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
