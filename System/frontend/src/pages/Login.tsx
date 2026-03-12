import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, Typography, message, Alert } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuth } from '../auth'

const { Title, Text } = Typography

export default function LoginPage() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { login } = useAuth()

  const onFinish = async () => {
    const values = await form.validateFields()
    try {
      await login(values.username, values.password)
      message.success('立即登录成功，欢迎回来')
      navigate('/dashboard', { replace: true })
    } catch (e: any) {
      message.error(`立即登录失败： ${e.message}`)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f0f2f5' }}>
      <Card style={{ width: 460 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 4 }}>Ozon 智能运营系统</Title>
        <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 16 }}>登录后进入运营总控台，查看今日优先事项与执行闭环。</Text>
        <Alert type="info" showIcon style={{ marginBottom: 16 }} message="轻量认证模式" description="当前为轻量认证实现，适合运营后台日常验证。" />
        <Form form={form} layout="vertical" initialValues={{ username: 'operator', password: '123456' }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
          </Form.Item>
          <Button type="primary" block onClick={onFinish}>立即登录</Button>
        </Form>
      </Card>
    </div>
  )
}
