import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Button, Avatar, Dropdown, Badge, Space } from 'antd'
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
  LogoutOutlined
} from '@ant-design/icons'

const { Header, Sider, Content } = AntLayout

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  // 菜单项
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '运营总览',
    },
    {
      key: '/import',
      icon: <UploadOutlined />,
      label: '数据导入',
    },
    {
      key: '/profit',
      icon: <CalculatorOutlined />,
      label: '利润求解器',
    },
    {
      key: '/abc',
      icon: <BarChartOutlined />,
      label: 'ABC分析',
    },
    {
      key: '/price',
      icon: <DollarOutlined />,
      label: '价格竞争力',
    },
    {
      key: '/funnel',
      icon: <FunnelPlotOutlined />,
      label: '转化漏斗',
    },
    {
      key: '/inventory',
      icon: <WarningOutlined />,
      label: '库存预警',
    },
    {
      key: '/ads',
      icon: <AimOutlined />,
      label: '广告管理',
    },
    {
      key: '/strategy',
      icon: <BulbOutlined />,
      label: '策略清单',
    },
    {
      key: '/decision',
      icon: <ThunderboltOutlined />,
      label: '智能决策',
    },
  ]

  // 用户菜单
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人设置',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ]

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  // 处理用户菜单点击
  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      console.log('退出登录')
    }
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: collapsed ? '16px' : '20px',
          fontWeight: 'bold',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          {collapsed ? 'V5.1' : 'V5.1 运营系统'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>

      {/* 主内容区 */}
      <AntLayout style={{ marginLeft: collapsed ? 80 : 200, transition: 'all 0.2s' }}>
        {/* 顶部导航栏 */}
        <Header style={{
          padding: '0 24px',
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0, 21, 41, 0.08)'
        }}>
          <div style={{ fontSize: '16px', fontWeight: 500 }}>
            V5.1 跨境电商智能运营系统
          </div>

          <Space>
            {/* 通知图标 */}
            <Badge count={5} size="small">
              <Button
                type="text"
                icon={<BellOutlined />}
                style={{ fontSize: '16px' }}
              />
            </Badge>

            {/* 用户下拉菜单 */}
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>运营专员</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 内容区域 */}
        <Content style={{
          margin: 0,
          background: '#f0f2f5',
          overflow: 'auto',
          minHeight: 'calc(100vh - 64px)'
        }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
