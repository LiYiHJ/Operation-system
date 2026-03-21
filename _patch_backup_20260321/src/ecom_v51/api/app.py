"""
Flask API层 - 前后端分离架构
只提供 RESTful API，不渲染模板
"""

from flask import Flask, jsonify
import os

from ecom_v51.db.session import get_engine, get_session
from ecom_v51.config.settings import settings

from ecom_v51.services import (
    DashboardService,
    ProductService,
    ProfitService,
    StrategyTaskService,
)

from .routes.dashboard import dashboard_bp
from .routes.products import products_bp
from .routes.profit import profit_bp
from .routes.strategy import strategy_bp
from .routes.import_route import import_bp
from .routes.analysis import analysis_bp
from .routes.auth import auth_bp
from .routes.reminder import reminder_bp
from .routes.integration import integration_bp
from .routes.ads import ads_bp


def create_app(config_name: str = 'default'):
    app = Flask(__name__)

    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = False
    elif config_name == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    else:
        app.config['DEBUG'] = bool(settings.debug)
        app.config['TESTING'] = False

    app.config.update(
        SECRET_KEY=settings.secret_key,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), '../../uploads'),
    )

    if settings.APP_ENV == 'production' and settings.secret_key == 'dev-secret-key-change-in-production':
        raise RuntimeError('生产环境必须设置安全的 SECRET_KEY')

    try:
        from flask_cors import CORS

        CORS(app, resources={
            r"/api/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": ["Content-Type"],
            }
        })
    except ImportError:
        print("⚠️ 警告: flask-cors 未安装，跨域功能已禁用")
        print("安装: pip install flask-cors")

    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(profit_bp, url_prefix='/api/profit')
    app.register_blueprint(strategy_bp, url_prefix='/api/strategy')
    app.register_blueprint(import_bp, url_prefix='/api/import')
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(reminder_bp, url_prefix='/api/reminders')
    app.register_blueprint(integration_bp, url_prefix='/api/integration')
    app.register_blueprint(ads_bp, url_prefix='/api/ads')

    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            'status': 'ok',
            'service': 'ecom_v51_api',
            'version': '1.0.0',
        })

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal Server Error'}), 500

    return app


app = create_app()


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("运营系统 Flask API (前后端分离)")
    print("=" * 70)
    print("API地址: http://localhost:5000/api")
    print("健康检查: http://localhost:5000/api/health")
    print("前端地址: http://localhost:5173")
    print("=" * 70 + "\n")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=bool(settings.debug))
