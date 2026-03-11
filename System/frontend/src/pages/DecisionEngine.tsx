import React, { useState, useMemo } from 'react'
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Alert,
  Space,
  Modal,
  Input,
  Select,
  Tabs,
  Progress,
  Typography,
  Statistic,
  Badge,
  Tooltip,
  message
} from 'antd'
import {
  AlertOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BellOutlined,
  EyeOutlined,
  CaretRightOutlined,
  SearchOutlined,
  FilterOutlined,
  SortAscendingOutlined,
  ThunderboltOutlined,
  NotificationOutlined,
  CloseOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ArrowRightOutlined,
  TrophyOutlined,
  StarOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'

const { Title, Text } = Typography
const { Search } = Input

// ===== 智能决策引擎 - Ant Design 版本 =====

// 示例数据
const mockStrategies = [
  {
    id: 'strategy-001',
    priority: 'P0',
    sku: 'HAA132-01',
    type: '库存',
    issue: '库存仅剩 3 天销量',
    current_value: '库存: 45 件, 日销: 15 件',
    suggestion: '立即补货，联系供应商',
    impact: '预计 3 天后断货，损失订单约 ¥2,340/天',
    status: '待处理',
    created_at: '2026-03-08 16:00:00',
    confidence: 0.95,
    auto_executable: true
  },
  {
    id: 'strategy-002',
    priority: 'P0',
    sku: 'LADY-089',
    type: '定价',
    issue: '净利率 -5%，处于亏损状态',
    current_value: '售价: ¥199, 成本: ¥209',
    suggestion: '提高售价 15% 或降低采购成本',
    impact: '每单亏损 ¥10',
    status: '待处理',
    created_at: '2026-03-08 16:00:00',
    confidence: 0.92,
    auto_executable: true
  },
  {
    id: 'strategy-003',
    priority: 'P1',
    sku: 'HBB256-03',
    type: '转化',
    issue: 'CTR 仅 1.2%，低于平均 2.1%',
    current_value: '曝光: 5,000, 点击: 60',
    suggestion: '优化主图，测试新标题',
    impact: '流量浪费，转化潜力未释放',
    status: '进行中',
    created_at: '2026-03-08 16:00:00',
    confidence: 0.88,
    auto_executable: false
  },
  {
    id: 'strategy-004',
    priority: 'P1',
    sku: 'TOY-445',
    type: '广告',
    issue: 'ROAS = 1.5，广告效率低',
    current_value: '广告费: ¥300, 收入: ¥450',
    suggestion: '降投低效关键词，提高精准度',
    impact: '广告投入产出比低',
    status: '进行中',
    created_at: '2026-03-08 16:00:00',
    confidence: 0.90,
    auto_executable: true
  },
  {
    id: 'strategy-005',
    priority: 'P2',
    sku: 'ELEC-023',
    type: '风控',
    issue: '评分 4.2，较上月下降 0.3',
    current_value: '评价数: 128, 差评率: 8%',
    suggestion: '排查差评原因，优化产品质量',
    impact: '长期影响转化率和搜索权重',
    status: '待处理',
    created_at: '2026-03-08 16:00:00',
    confidence: 0.85,
    auto_executable: false
  },
  {
    id: 'strategy-006',
    priority: 'P3',
    sku: 'HOME-567',
    type: '库存',
    issue: '库存积压，可销天数 90 天',
    current_value: '库存: 320 件, 日销: 3.5 件',
    suggestion: '降价促销，清理库存',
    impact: '资金占用，仓储成本增加',
    status: '已完成',
    created_at: '2026-03-08 12:00:00',
    confidence: 0.80,
    auto_executable: true
  }
]

const mockMetrics = [
  { sku: 'HAA132-01', ctr: 2.3, conversion: 4.2, rating: 4.6, roas: 3.2, daysOfSupply: 3 },
  { sku: 'HBB256-03', ctr: 1.2, conversion: 2.8, rating: 4.3, roas: 2.1, daysOfSupply: 15 },
  { sku: 'LADY-089', ctr: 2.8, conversion: 3.5, rating: 4.1, roas: 1.8, daysOfSupply: 8 },
  { sku: 'TOY-445', ctr: 1.9, conversion: 3.2, rating: 4.7, roas: 1.5, daysOfSupply: 22 },
  { sku: 'ELEC-023', ctr: 2.5, conversion: 4.0, rating: 4.2, roas: 2.8, daysOfSupply: 18 }
]

// 智能推荐
const smartRecommendations = [
  {
    type: 'auto_execute',
    title: '🤖 智能推荐：一键修复 P0 问题',
    description: '系统检测到 2 个 P0 问题可自动执行，预计节省损失 ¥5,680',
    action: '立即自动执行',
    impact: '避免断货 + 停止亏损'
  },
  {
    type: 'priority',
    title: '⚡️ 优先级建议',
    description: '建议先处理 HAA132-01 库存问题，再处理 LADY-089 定价问题',
    action: '查看详情',
    impact: '最大化收益'
  },
  {
    type: 'trend',
    title: '📈 趋势预警',
    description: 'HBB256-03 的 CTR 持续下降 3 天，建议尽快优化',
    action: '查看趋势',
    impact: '防止进一步恶化'
  }
]

export default function DecisionEngine() {
  // ===== 状态管理 =====
  const [strategies, setStrategies] = useState(mockStrategies)
  const [selectedStrategy, setSelectedStrategy] = useState<any>(null)
  const [showAlert, setShowAlert] = useState(true)

  // 筛选和排序
  const [searchText, setSearchText] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('priority')

  // 标签页
  const [tabValue, setTabValue] = useState('0')

  // 自动执行进度
  const [autoExecuting, setAutoExecuting] = useState(false)

  // ===== 智能计算 =====
  // 健康度评分
  const healthScore = useMemo(() => {
    const p0Count = strategies.filter(s => s.priority === 'P0' && s.status !== '已完成').length
    const p1Count = strategies.filter(s => s.priority === 'P1' && s.status !== '已完成').length
    const p2Count = strategies.filter(s => s.priority === 'P2' && s.status !== '已完成').length
    const p3Count = strategies.filter(s => s.priority === 'P3' && s.status !== '已完成').length

    return Math.max(0, 100 - (p0Count * 10 + p1Count * 5 + p2Count * 2 + p3Count * 1))
  }, [strategies])

  // 筛选后的策略
  const filteredStrategies = useMemo(() => {
    let result = [...strategies]

    if (searchText) {
      result = result.filter(s =>
        s.sku.toLowerCase().includes(searchText.toLowerCase()) ||
        s.issue.toLowerCase().includes(searchText.toLowerCase()) ||
        s.suggestion.toLowerCase().includes(searchText.toLowerCase())
      )
    }

    if (priorityFilter !== 'all') {
      result = result.filter(s => s.priority === priorityFilter)
    }

    if (typeFilter !== 'all') {
      result = result.filter(s => s.type === typeFilter)
    }

    if (statusFilter !== 'all') {
      result = result.filter(s => s.status === statusFilter)
    }

    const priorityOrder: Record<string, number> = { 'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3 }
    if (sortBy === 'priority') {
      result.sort((a, b) => (priorityOrder[a.priority] || 0) - (priorityOrder[b.priority] || 0))
    } else if (sortBy === 'created_at') {
      result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    } else if (sortBy === 'confidence') {
      result.sort((a, b) => b.confidence - a.confidence)
    }

    return result
  }, [strategies, searchText, priorityFilter, typeFilter, statusFilter, sortBy])

  // 图表数据
  const priorityChartData = useMemo(() => {
    const counts: any = { 'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0 }
    strategies.forEach(s => counts[s.priority]++)
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [strategies])

  const typeChartData = useMemo(() => {
    const counts: any = {}
    strategies.forEach(s => {
      counts[s.type] = (counts[s.type] || 0) + 1
    })
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [strategies])

  // ===== 交互功能 =====
  const updateStrategyStatus = (id: string, newStatus: string) => {
    setStrategies(strategies.map(s =>
      s.id === id ? { ...s, status: newStatus } : s
    ))
    message.success(`✅ 策略已更新为：${newStatus}`)
    setSelectedStrategy(null)
  }

  const autoExecuteAll = async () => {
    setAutoExecuting(true)

    const executableP0s = strategies.filter(s =>
      s.priority === 'P0' && s.auto_executable && s.status !== '已完成'
    )

    for (let i = 0; i < executableP0s.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      updateStrategyStatus(executableP0s[i].id, '已完成')
    }

    setAutoExecuting(false)
    message.success(`🎉 已自动执行 ${executableP0s.length} 个 P0 策略，预计节省损失 ¥5,680`)
  }

  // ===== 辅助函数 =====
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P0': return 'red'
      case 'P1': return 'orange'
      case 'P2': return 'blue'
      case 'P3': return 'green'
      default: return 'default'
    }
  }

  const getPriorityBgColor = (priority: string) => {
    switch (priority) {
      case 'P0': return '#fff1f0'
      case 'P1': return '#fff7e6'
      case 'P2': return '#e6f7ff'
      case 'P3': return '#f6ffed'
      default: return '#fafafa'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case '待处理': return <ClockCircleOutlined style={{ color: '#ff4d4f' }} />
      case '进行中': return <CaretRightOutlined style={{ color: '#faad14' }} />
      case '已完成': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      default: return null
    }
  }

  const getMetricStatus = (value: number, type: string) => {
    const thresholds: any = {
      ctr: { good: 2.0, bad: 1.5 },
      conversion: { good: 3.5, bad: 2.5 },
      rating: { good: 4.5, bad: 4.0 },
      roas: { good: 2.0, bad: 1.5 },
      daysOfSupply: { good: 14, bad: 7 }
    }

    const threshold = thresholds[type]
    if (!threshold) return 'normal'

    if (type === 'daysOfSupply') {
      if (value < threshold.bad) return 'critical'
      if (value < threshold.good) return 'warning'
      return 'good'
    }

    if (value >= threshold.good) return 'good'
    if (value >= threshold.bad) return 'warning'
    return 'critical'
  }

  const COLORS = ['#ff4d4f', '#faad14', '#1890ff', '#52c41a']

  const p0Count = strategies.filter(s => s.priority === 'P0' && s.status !== '已完成').length
  const p1Count = strategies.filter(s => s.priority === 'P1' && s.status !== '已完成').length

  // ECharts 配置
  const priorityChartOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: { show: true, formatter: '{b}: {c}' },
      data: priorityChartData.map((item, index) => ({
        value: item.value,
        name: item.name,
        itemStyle: { color: COLORS[index] }
      }))
    }]
  }

  const typeChartOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'category', data: typeChartData.map(item => item.name) },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: typeChartData.map(item => item.value),
      itemStyle: { color: '#1890ff' },
      label: { show: true, position: 'top' }
    }]
  }

  // 表格列定义
  const columns = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => (
        <Tag color={getPriorityColor(priority)} icon={<AlertOutlined />}>
          {priority}
        </Tag>
      )
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag>{type}</Tag>
    },
    {
      title: '问题描述',
      dataIndex: 'issue',
      key: 'issue',
      width: 200,
      render: (text: string, record: any) => (
        <div>
          <Text>{text}</Text>
          <br />
          <Text type="danger" style={{ fontSize: '12px' }}>{record.impact}</Text>
        </div>
      )
    },
    {
      title: '建议操作',
      dataIndex: 'suggestion',
      key: 'suggestion',
      width: 200,
      ellipsis: true
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Space>
          <Progress
            percent={confidence * 100}
            size="small"
            style={{ width: 60 }}
            strokeColor={confidence >= 0.9 ? '#52c41a' : '#faad14'}
          />
          <Text>{Math.round(confidence * 100)}%</Text>
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag
          icon={getStatusIcon(status)}
          color={status === '已完成' ? 'success' : status === '进行中' ? 'warning' : 'error'}
        >
          {status}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <Space>
          {record.auto_executable && record.status !== '已完成' && (
            <Tooltip title="自动执行">
              <Button
                type="link"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={() => updateStrategyStatus(record.id, '已完成')}
              />
            </Tooltip>
          )}
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => setSelectedStrategy(record)}
            />
          </Tooltip>
        </Space>
      )
    }
  ]

  // 指标跟踪表格列
  const metricColumns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: 'CTR',
      dataIndex: 'ctr',
      key: 'ctr',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          unit="%"
          status={getMetricStatus(value, 'ctr')}
        />
      )
    },
    {
      title: '转化率',
      dataIndex: 'conversion',
      key: 'conversion',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          unit="%"
          status={getMetricStatus(value, 'conversion')}
        />
      )
    },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          status={getMetricStatus(value, 'rating')}
        />
      )
    },
    {
      title: 'ROAS',
      dataIndex: 'roas',
      key: 'roas',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          status={getMetricStatus(value, 'roas')}
        />
      )
    },
    {
      title: '库存天数',
      dataIndex: 'daysOfSupply',
      key: 'daysOfSupply',
      align: 'center' as const,
      render: (value: number) => (
        <MetricBadge
          value={value}
          unit="天"
          status={getMetricStatus(value, 'daysOfSupply')}
        />
      )
    }
  ]

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 标题 */}
      <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
        <Title level={3} style={{ margin: 0 }}>🧠 智能决策引擎</Title>
        <Tag color="blue">V5.1</Tag>
        <Tag color={healthScore >= 80 ? 'success' : healthScore >= 60 ? 'warning' : 'error'}>
          健康度: {healthScore}
        </Tag>
      </div>

      {/* 智能推荐 */}
      {showAlert && (
        <Alert
          type="info"
          icon={<ThunderboltOutlined />}
          message="🤖 智能推荐"
          description={
            <div>
              {smartRecommendations.map((rec, i) => (
                <div
                  key={i}
                  style={{
                    marginTop: i > 0 ? '8px' : 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px'
                  }}
                >
                  <Text style={{ flex: 1 }}>
                    {rec.title}: {rec.description}
                  </Text>
                  <Button size="small" type="primary" ghost>
                    {rec.action}
                  </Button>
                </div>
              ))}
            </div>
          }
          closable
          onClose={() => setShowAlert(false)}
          style={{ marginBottom: '24px' }}
        />
      )}

      {/* P0 紧急告警 */}
      {p0Count > 0 && (
        <Alert
          type="error"
          icon={<NotificationOutlined />}
          message={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Text strong style={{ fontSize: '16px' }}>
                🚨 检测到 {p0Count} 个 P0 级别紧急问题
              </Text>
              <Button
                type="primary"
                danger
                onClick={autoExecuteAll}
                loading={autoExecuting}
                icon={<ThunderboltOutlined />}
              >
                🤖 一键自动执行
              </Button>
            </div>
          }
          description={
            <div style={{ marginTop: '12px' }}>
              {strategies.filter(s => s.priority === 'P0' && s.status !== '已完成').map(s => (
                <div
                  key={s.id}
                  style={{
                    marginTop: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <Tag color="red">{s.priority}</Tag>
                  <Text><strong>{s.sku}</strong> - {s.issue}</Text>
                  {s.auto_executable && (
                    <Tag color="blue" icon={<ThunderboltOutlined />}>可自动执行</Tag>
                  )}
                  <Button
                    size="small"
                    type="primary"
                    danger
                    onClick={() => setSelectedStrategy(s)}
                  >
                    立即处理
                  </Button>
                </div>
              ))}
            </div>
          }
          style={{ marginBottom: '24px' }}
        />
      )}

      {/* 标签页 */}
      <Tabs
        activeKey={tabValue}
        onChange={setTabValue}
        items={[
          {
            key: '0',
            label: `📋 策略清单 (${filteredStrategies.length})`,
            children: (
              <Row gutter={16}>
                {/* 左侧：健康度 + 统计 */}
                <Col span={6}>
                  <Card style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Title level={5}>🏥 健康度评分</Title>
                    <div style={{ margin: '24px 0' }}>
                      <Progress
                        type="circle"
                        percent={healthScore}
                        strokeColor={
                          healthScore >= 80 ? '#52c41a' :
                          healthScore >= 60 ? '#faad14' : '#ff4d4f'
                        }
                        format={percent => (
                          <Text strong style={{ fontSize: '32px' }}>{percent}</Text>
                        )}
                      />
                    </div>
                  </Card>
                  <Card>
                    <Row gutter={16}>
                      <Col span={12}>
                        <div style={{
                          textAlign: 'center',
                          padding: '16px',
                          background: '#fff1f0',
                          borderRadius: '8px'
                        }}>
                          <Title level={4} style={{ color: '#ff4d4f', margin: 0 }}>
                            {p0Count}
                          </Title>
                          <Text>🔴 紧急</Text>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div style={{
                          textAlign: 'center',
                          padding: '16px',
                          background: '#fff7e6',
                          borderRadius: '8px'
                        }}>
                          <Title level={4} style={{ color: '#faad14', margin: 0 }}>
                            {p1Count}
                          </Title>
                          <Text>🟠 严重</Text>
                        </div>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 右侧：策略表格 */}
                <Col span={18}>
                  <Card>
                    {/* 筛选和搜索 */}
                    <div style={{
                      marginBottom: '16px',
                      display: 'flex',
                      gap: '8px',
                      flexWrap: 'wrap'
                    }}>
                      <Input
                        placeholder="搜索 SKU / 问题 / 建议"
                        prefix={<SearchOutlined />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        style={{ width: 250 }}
                      />
                      <Select
                        value={priorityFilter}
                        onChange={setPriorityFilter}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="all">全部优先级</Select.Option>
                        <Select.Option value="P0">P0</Select.Option>
                        <Select.Option value="P1">P1</Select.Option>
                        <Select.Option value="P2">P2</Select.Option>
                        <Select.Option value="P3">P3</Select.Option>
                      </Select>
                      <Select
                        value={typeFilter}
                        onChange={setTypeFilter}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="all">全部类型</Select.Option>
                        <Select.Option value="库存">库存</Select.Option>
                        <Select.Option value="定价">定价</Select.Option>
                        <Select.Option value="转化">转化</Select.Option>
                        <Select.Option value="广告">广告</Select.Option>
                        <Select.Option value="风控">风控</Select.Option>
                      </Select>
                      <Select
                        value={statusFilter}
                        onChange={setStatusFilter}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="all">全部状态</Select.Option>
                        <Select.Option value="待处理">待处理</Select.Option>
                        <Select.Option value="进行中">进行中</Select.Option>
                        <Select.Option value="已完成">已完成</Select.Option>
                      </Select>

                      <Select
                        value={sortBy}
                        onChange={setSortBy}
                        style={{ width: 120 }}
                      >
                        <Select.Option value="priority">按优先级</Select.Option>
                        <Select.Option value="created_at">按时间</Select.Option>
                        <Select.Option value="confidence">按置信度</Select.Option>
                      </Select>
                      <Text type="secondary" style={{ alignSelf: 'center' }}>
                        显示 {filteredStrategies.length} / {strategies.length} 条
                      </Text>
                    </div>

                    {/* 表格 */}
                    <Table
                      dataSource={filteredStrategies}
                      columns={columns}
                      rowKey="id"
                      pagination={false}
                      scroll={{ x: 1200 }}
                      onRow={(record) => ({
                        onClick: () => setSelectedStrategy(record),
                        style: {
                          cursor: 'pointer',
                          background: getPriorityBgColor(record.priority)
                        }
                      })}
                    />
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: '1',
            label: '📊 可视化分析',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Card title="📊 优先级分布">
                    <ReactECharts option={priorityChartOption} style={{ height: '300px' }} />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title="📈 问题类型分布">
                    <ReactECharts option={typeChartOption} style={{ height: '300px' }} />
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: '2',
            label: '🔍 指标跟踪',
            children: (
              <Card title="🔍 指标跟踪">
                <Table
                  dataSource={mockMetrics}
                  columns={metricColumns}
                  rowKey="sku"
                  pagination={false}
                />
              </Card>
            )
          }
        ]}
      />

      {/* 详情弹窗 */}
      <Modal
        title={
          selectedStrategy && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Tag color={getPriorityColor(selectedStrategy.priority)} icon={<AlertOutlined />}>
                {selectedStrategy.priority}
              </Tag>
              <Text strong>{selectedStrategy.sku} - {selectedStrategy.issue}</Text>
            </div>
          )
        }
        open={!!selectedStrategy}
        onCancel={() => setSelectedStrategy(null)}
        footer={
          selectedStrategy && selectedStrategy.status !== '已完成' ? [
            <Button key="close" onClick={() => setSelectedStrategy(null)}>关闭</Button>,
            <Button
              key="inProgress"
              type="default"
              onClick={() => updateStrategyStatus(selectedStrategy.id, '进行中')}
            >
              标记为进行中
            </Button>,
            <Button
              key="complete"
              type="primary"
              icon={selectedStrategy.auto_executable ? <ThunderboltOutlined /> : <CheckCircleOutlined />}
              onClick={() => updateStrategyStatus(selectedStrategy.id, '已完成')}
            >
              {selectedStrategy.auto_executable ? '自动执行' : '标记为已完成'}
            </Button>
          ] : [
            <Button key="close" onClick={() => setSelectedStrategy(null)}>关闭</Button>
          ]
        }
        width={800}
      >
        {selectedStrategy && (
          <div>
            <Title level={5}>📊 问题诊断</Title>
            <Card size="small" style={{ background: '#f5f5f5', marginBottom: '16px' }}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text type="secondary">问题类型</Text>
                  <br />
                  <Text strong>{selectedStrategy.type}</Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">当前状态</Text>
                  <br />
                  <Text strong>{selectedStrategy.current_value}</Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">影响范围</Text>
                  <br />
                  <Text strong type="danger">{selectedStrategy.impact}</Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">AI 置信度</Text>
                  <br />
                  <Space>
                    <Progress
                      percent={selectedStrategy.confidence * 100}
                      size="small"
                      style={{ width: 100 }}
                      strokeColor={selectedStrategy.confidence >= 0.9 ? '#52c41a' : '#faad14'}
                    />
                    <Text strong>{Math.round(selectedStrategy.confidence * 100)}%</Text>
                  </Space>
                </Col>
              </Row>
            </Card>

            <Title level={5}>🎯 执行建议</Title>
            <Card size="small" style={{ background: '#e6f7ff', marginBottom: '16px' }}>
              <Text>{selectedStrategy.suggestion}</Text>
            </Card>

            {selectedStrategy.auto_executable && (
              <Alert
                type="success"
                icon={<ThunderboltOutlined />}
                message="🤖 智能推荐：自动执行"
                description="系统可自动执行此策略，无需人工干预"
                style={{ marginTop: '16px' }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

// 辅助组件
function MetricBadge({ value, unit = '', status }: { value: number; unit?: string; status: string }) {
  const getColor = () => {
    switch (status) {
      case 'good': return '#52c41a'
      case 'warning': return '#faad14'
      case 'critical': return '#ff4d4f'
      default: return '#8c8c8c'
    }
  }

  const getIcon = () => {
    switch (status) {
      case 'good': return '✓'
      case 'warning': return '⚠️'
      case 'critical': return '⛔️'
      default: return ''
    }
  }

  const getBgColor = () => {
    switch (status) {
      case 'good': return '#f6ffed'
      case 'warning': return '#fffbe6'
      case 'critical': return '#fff1f0'
      default: return '#fafafa'
    }
  }

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '4px 12px',
        borderRadius: '8px',
        background: getBgColor(),
        border: `2px solid ${getColor()}`
      }}
    >
      <Text strong style={{ color: getColor() }}>
        {value}{unit} {getIcon()}
      </Text>
    </div>
  )
}
