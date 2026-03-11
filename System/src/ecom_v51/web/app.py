from __future__ import annotations

import os

from flask import Flask

from ecom_v51.config.settings import settings
from ecom_v51.web.routes import register_blueprints


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.update(
        SECRET_KEY=settings.secret_key,
        ENV=settings.app_env,
        DEBUG=settings.debug,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 最大 50MB
        UPLOAD_FOLDER=os.path.join(os.path.dirname(__file__), '../../uploads'),
    )
    
    # 注册 Jinja2 过滤器
    @app.template_filter('number')
    def number_format(value):
        """格式化数字：添加千分位分隔符"""
        if value is None:
            return 0
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value
    
    register_blueprints(app)
    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=settings.debug)
