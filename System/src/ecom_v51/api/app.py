"""
Flask API层 - 前后端分离架构
只提供RESTful API 不渲染模板
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os

# 导入已有的session管理
from ecom_v51.db.session import get_engine, get_session
from ecom_v51.config.settings import settings

# 导入服务层
from ecom_v51.services import (
    DashboardService,
    ProductService,
    ProfitService,
    StrategyTaskService,
)

# 导入路由
from .routes.dashboard import dashboard_bp
from .routes.products import products_bp
from .routes.profit import profit_bp
from .routes.strategy import strategy_bp
from .routes.import_route import import_bp


def create_app(config_name='default'):  
    app = Flask(__name__)
    
    # 根据配置加载不同设置
    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = False
    elif config_name == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    
    # ... 其他配置
    # 配置
    app.config.update(
        SECRET_KEY=settings.secret_key,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50MB
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), '../../uploads'),
    )
    
    # CORS（允许React前端跨域）
        # CORS（允许React前端跨域）
    try:
        from flask_cors import CORS
        CORS(app, resources={
            r"/api/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": ["Content-Type"]
            }
        })
    except ImportError:
        print("⚠️ 警告: flask-cors 未安装，跨域功能已禁用")
        print("安装: pip install flask-cors")

    
    # 注册blueprints
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(profit_bp, url_prefix='/api/profit')
    app.register_blueprint(strategy_bp, url_prefix='/api/strategy')
    app.register_blueprint(import_bp, url_prefix='/api/import')
    
    # 健康检查
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'ok',
            'service': 'ecom_v51_api',
            'version': '5.1.0'
        })
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal Server Error'}), 500
    
    return app


# 创建应用实例
app = create_app()


if __name__ == '__main__':
    print("\n" + "="*70)
    print("V5.1 Flask API (前后端分离)")
    print("="*70)
    print(f"API地址: http://localhost:5000/api")
    print(f"健康检查: http://localhost:5000/api/health")
    print(f"前端地址: http://localhost:5173")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
