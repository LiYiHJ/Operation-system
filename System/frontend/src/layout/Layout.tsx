import { useMemo, useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Button, Avatar, Dropdown, Badge, Space, Drawer, List, Tag, Typography } from 'antd'
import {
  DashboardOutlined,
  UploadOutlined,
  BarChartOutlined,
  DollarOutlined,
  FunnelPlotOutlined,
  WarningOutlined,
  AimOutlined,
  BulbOutlined,
  ThunderboltOutlined,
  CalculatorOutlined,
  UserOutlined,
  BellOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { reminderApi } from '../services/api'
import { useAuth } from '../auth'
import { sourcePageLabels } from '../utils/labels'

const { Header, Sider, Content } = AntLayout
const { Text } = Typography

const categoryColor: Record<string, string> = {
  new_orders: 'blue',
  new_reviews: 'purple',
  system_alerts: 'red',
  pending_confirmations: 'orange',
  execution_writeback: 'green',
  import_exceptions: 'magenta',
}

const categoryLabel: Record<string, string> = {
  new_orders: '新订单',
  new_reviews: '新评价',
  system_alerts: '系统告警',
  pending_confirmations: '待确认动作',
  execution_writeback: '执行回写',
  import_exceptions: '导入异常',
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const [reminderOpen, setReminderOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  const { data: reminderData, refetch } = useQuery({ queryKey: ['reminders'], queryFn: () => reminderApi.list({ shopId: 1 }), refetchInterval: 60_000 })
  const reminderCount = reminderData?.summary?.unread || 0

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '运营总览' },
    { key: '/import', icon: <UploadOutlined />, label: '数据导入' },
    { key: '/profit', icon: <CalculatorOutlined />, label: '利润求解器' },
    { key: '/abc', icon: <BarChartOutlined />, label: 'ABC分析' },
    { key: '/price', icon: <DollarOutlined />, label: '价格竞争力' },
    { key: '/funnel', icon: <FunnelPlotOutlined />, label: '转化漏斗' },
    { key: '/inventory', icon: <WarningOutlined />, label: '库存预警' },
    { key: '/ads', icon: <AimOutlined />, label: '广告管理' },
    { key: '/strategy', icon: <BulbOutlined />, label: '策略清单' },
    { key: '/decision', icon: <ThunderboltOutlined />, label: '智能决策' },
  ]

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人设置' },
    { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
  ]

  const handleUserMenuClick = async ({ key }: { key: string }) => {
    if (key === 'logout') {
      await logout()
      navigate('/login', { replace: true })
    }
  }

  const summaryTags = useMemo(() => [
    { key: 'new_orders', label: '新订单', value: reminderData?.summary?.new_orders || 0 },
    { key: 'new_reviews', label: '新评价', value: reminderData?.summary?.new_reviews || 0 },
    { key: 'system_alerts', label: '系统告警', value: reminderData?.summary?.system_alerts || 0 },
    { key: 'pending_confirmations', label: '待确认', value: reminderData?.summary?.pending_confirmations || 0 },
    { key: 'execution_writeback', label: '执行回写', value: reminderData?.summary?.execution_writeback || 0 },
    { key: 'import_exceptions', label: '导入异常', value: reminderData?.summary?.import_exceptions || 0 },
  ], [reminderData])

  const openReminder = async () => {
    setReminderOpen(true)
    await reminderApi.ack()
    refetch()
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} style={{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: collapsed ? '16px' : '20px', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
          {collapsed ? 'V5.1' : 'V5.1 运营系统'}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} onClick={({ key }) => navigate(key)} />
      </Sider>

      <AntLayout style={{ marginLeft: collapsed ? 80 : 200, transition: 'all 0.2s' }}>
        <Header style={{ padding: '0 24px', background: '#fff', display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', boxShadow: '0 1px 4px rgba(0, 21, 41, 0.08)' }}>
          <Space align="center">
            <Text type="secondary" style={{ fontSize: 12, opacity: 0.6 }}>总览</Text>
          </Space>
          <div style={{ fontSize: '16px', fontWeight: 600, textAlign: 'center', whiteSpace: 'nowrap' }}>V5.1 跨境电商智能运营系统</div>
          <Space style={{ justifySelf: 'end' }}>
            <Badge count={reminderCount} size="small">
              <Button type="text" icon={<BellOutlined />} style={{ fontSize: '16px' }} onClick={openReminder} />
            </Badge>
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>{user?.displayName || '运营专员'}（{user?.role || 'operator'}）</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: 0, background: '#f0f2f5', overflow: 'auto', minHeight: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </AntLayout>

      <Drawer title="提醒中心（未读进入即置已读）" open={reminderOpen} onClose={() => setReminderOpen(false)} width={460}>
        <Space wrap style={{ marginBottom: 12 }}>
          {summaryTags.map((x) => <Tag key={x.key} color={categoryColor[x.key] || 'default'}>{x.label}: {x.value}</Tag>)}
        </Space>
        <List
          size="small"
          dataSource={reminderData?.items || []}
          renderItem={(x: any) => (
            <List.Item
              style={{ cursor: 'pointer' }}
              onClick={() => {
                setReminderOpen(false)
                if (x.target) navigate(x.target)
              }}
            >
              <Space direction="vertical" size={0} style={{ width: '100%' }}>
                <Space>
                  <Tag color={categoryColor[x.category] || 'default'}>{categoryLabel[x.category] || x.category}</Tag>
                  <Text type="secondary">{x.time ? new Date(x.time).toLocaleString('zh-CN') : '—'}</Text>
                </Space>
                <Text strong>{x.summary || x.title}</Text>
                <Text type="secondary">来源：{sourcePageLabels[x.source] || x.source || '系统模块'} · 跳转：{x.target || '—'}</Text>
                <Text style={{ color: '#1677ff' }}>点击此条可直达处理页面</Text>
              </Space>
            </List.Item>
          )}
        />
      </Drawer>
    </AntLayout>
  )
}
