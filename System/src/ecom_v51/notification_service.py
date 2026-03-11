"""
通知服务
支持邮件和 Telegram 通知
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import List, Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务基类"""
    
    def send(self, to: str, subject: str, message: str, **kwargs) -> bool:
        """
        发送通知
        
        Args:
            to: 接收者
            subject: 主题
            message: 消息内容
        
        Returns:
            是否成功
        """
        raise NotImplementedError


class EmailService(NotificationService):
    """
    邮件通知服务
    
    支持多种邮箱：QQ邮箱、163邮箱、Gmail、企业邮箱等
    """
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_name: str = "Ozon 智能决策引擎"
    ):
        """
        初始化邮件服务
        
        Args:
            smtp_server: SMTP 服务器地址
            smtp_port: SMTP 端口
            username: 邮箱账号
            password: 邮箱密码/授权码
            from_name: 发件人名称
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_name = from_name
    
    def send(
        self,
        to: str,
        subject: str,
        message: str,
        html: bool = True,
        cc: List[str] = None,
        **kwargs
    ) -> bool:
        """
        发送邮件
        
        Args:
            to: 收件人邮箱
            subject: 邮件主题
            message: 邮件内容
            html: 是否为 HTML 格式
            cc: 抄送列表
        
        Returns:
            是否成功
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.username}>"
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # 添加内容
            if html:
                msg.attach(MIMEText(message, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                
                recipients = [to]
                if cc:
                    recipients.extend(cc)
                
                server.sendmail(self.username, recipients, msg.as_string())
            
            logger.info(f"✅ 邮件发送成功: {to}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {e}")
            return False
    
    def send_alert_email(
        self,
        to: str,
        alert_type: str,
        alerts: List[Dict]
    ) -> bool:
        """
        发送告警邮件（专用模板）
        
        Args:
            to: 收件人邮箱
            alert_type: 告警类型（P0/P1/库存/价格）
            alerts: 告警列表
        
        Returns:
            是否成功
        """
        # 构建邮件内容
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%); 
                          color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .alert {{ border-left: 4px solid #f44336; padding: 15px; margin: 15px 0; 
                         background: #ffebee; }}
                .alert h3 {{ margin-top: 0; color: #d32f2f; }}
                .footer {{ padding: 20px; text-align: center; color: #999; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #f44336; 
                       color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 Ozon 智能告警</h1>
                <p>{alert_type} 问题需要立即处理</p>
                <p>时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="content">
                <h2>检测到 {len(alerts)} 个问题</h2>
        """
        
        for alert in alerts:
            html_content += f"""
                <div class="alert">
                    <h3>{alert.get('icon', '⚠️')} {alert.get('title', '未知问题')}</h3>
                    <p><strong>SKU:</strong> {alert.get('sku', 'N/A')}</p>
                    <p><strong>问题:</strong> {alert.get('issue', 'N/A')}</p>
                    <p><strong>影响:</strong> {alert.get('impact', 'N/A')}</p>
                    <p><strong>建议:</strong> {alert.get('suggestion', 'N/A')}</p>
                </div>
            """
        
        html_content += """
                <div style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:5173/decision" class="btn">立即查看详情</a>
                </div>
            </div>
            
            <div class="footer">
                <p>此邮件由 Ozon 智能决策引擎自动发送</p>
                <p>如需停止接收，请在系统中关闭邮件通知</p>
            </div>
        </body>
        </html>
        """
        
        return self.send(
            to=to,
            subject=f"🚨 Ozon {alert_type} 告警 - {len(alerts)} 个问题需要处理",
            message=html_content,
            html=True
        )


class TelegramService(NotificationService):
    """
    Telegram 通知服务
    
    使用 Bot API 发送消息
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        初始化 Telegram 服务
        
        Args:
            bot_token: Bot Token
            chat_id: Chat ID（可以是用户ID、群组ID、频道用户名）
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send(
        self,
        to: str = None,
        subject: str = "",
        message: str = "",
        parse_mode: str = "Markdown",
        **kwargs
    ) -> bool:
        """
        发送 Telegram 消息
        
        Args:
            to: Chat ID（可选，默认使用初始化时的 chat_id）
            subject: 主题（会添加到消息开头）
            message: 消息内容
            parse_mode: 解析模式（Markdown/HTML）
        
        Returns:
            是否成功
        """
        try:
            chat_id = to or self.chat_id
            
            # 组合消息
            full_message = f"*{subject}*\n\n{message}" if subject else message
            
            # 发送消息
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": full_message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"✅ Telegram 消息发送成功: {chat_id}")
                return True
            else:
                logger.error(f"❌ Telegram 消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telegram 发送异常: {e}")
            return False
    
    def send_alert_message(
        self,
        alert_type: str,
        alerts: List[Dict]
    ) -> bool:
        """
        发送告警消息（专用格式）
        
        Args:
            alert_type: 告警类型
            alerts: 告警列表
        
        Returns:
            是否成功
        """
        # 构建消息
        message = f"🚨 *Ozon {alert_type} 告警*\n"
        message += f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"问题数量: {len(alerts)}\n\n"
        message += "━━━━━━━━━━━━━━━\n\n"
        
        for i, alert in enumerate(alerts, 1):
            message += f"{i}️⃣ *{alert.get('title', '未知问题')}*\n"
            message += f"• SKU: `{alert.get('sku', 'N/A')}`\n"
            message += f"• 问题: {alert.get('issue', 'N/A')}\n"
            message += f"• 影响: {alert.get('impact', 'N/A')}\n"
            message += f"• 建议: {alert.get('suggestion', 'N/A')}\n\n"
        
        message += "━━━━━━━━━━━━━━━\n"
        message += "[立即查看](http://localhost:5173/decision)"
        
        return self.send(
            subject=f"{alert_type} 紧急告警",
            message=message,
            parse_mode="Markdown"
        )
    
    def send_daily_report(
        self,
        report_data: Dict
    ) -> bool:
        """
        发送日报
        
        Args:
            report_data: 日报数据
        
        Returns:
            是否成功
        """
        message = f"""
📊 *Ozon 运营日报*
日期: {datetime.now().strftime('%Y-%m-%d')}

━━━━━━━━━━━━━━━

🏥 *健康度*: {report_data.get('health_score', 0)} 分

📦 *订单统计*:
• 总订单: {report_data.get('total_orders', 0)}
• FBO: {report_data.get('fbo_orders', 0)}
• FBS: {report_data.get('fbs_orders', 0)}

💰 *收入统计*:
• 总收入: ¥{report_data.get('total_revenue', 0):,.2f}

⚠️ *问题统计*:
• P0: {report_data.get('p0_count', 0)}
• P1: {report_data.get('p1_count', 0)}
• P2: {report_data.get('p2_count', 0)}

━━━━━━━━━━━━━━━

[查看详细报告](http://localhost:5173/dashboard)
"""
        
        return self.send(
            subject="运营日报",
            message=message,
            parse_mode="Markdown"
        )


# ===== 配置管理 =====

class NotificationConfig:
    """通知配置"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路径
        """
        self.email_config = {
            "enabled": False,
            "smtp_server": "smtp.qq.com",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "recipients": []
        }
        
        self.telegram_config = {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "parse_mode": "Markdown"
        }
        
        if config_file:
            self.load_config(config_file)
    
    def load_config(self, config_file: str):
        """加载配置文件"""
        import json
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                self.email_config.update(config.get('email', {}))
                self.telegram_config.update(config.get('telegram', {}))
                
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")
    
    def get_email_service(self) -> Optional[EmailService]:
        """获取邮件服务实例"""
        if not self.email_config["enabled"]:
            return None
        
        return EmailService(
            smtp_server=self.email_config["smtp_server"],
            smtp_port=self.email_config["smtp_port"],
            username=self.email_config["username"],
            password=self.email_config["password"]
        )
    
    def get_telegram_service(self) -> Optional[TelegramService]:
        """获取 Telegram 服务实例"""
        if not self.telegram_config["enabled"]:
            return None
        
        return TelegramService(
            bot_token=self.telegram_config["bot_token"],
            chat_id=self.telegram_config["chat_id"]
        )


# ===== 示例用法 =====

if __name__ == "__main__":
    # 示例：发送邮件
    email_service = EmailService(
        smtp_server="smtp.qq.com",
        smtp_port=587,
        username="your_email@qq.com",
        password="your_password"
    )
    
    email_service.send(
        to="recipient@example.com",
        subject="测试邮件",
        message="<h1>这是一封测试邮件</h1>",
        html=True
    )
    
    # 示例：发送 Telegram 消息
    telegram_service = TelegramService(
        bot_token="YOUR_BOT_TOKEN",
        chat_id="YOUR_CHAT_ID"
    )
    
    telegram_service.send(
        subject="测试消息",
        message="这是一条测试消息"
    )
