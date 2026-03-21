import { Row, Col, Card, Table, Tag, Statistic, Progress } from 'antd'
import ReactECharts from 'echarts-for-react'

export default function StrategyList() {
  const strategySummary = {
    P0: { total: 3, completed: 0, rate: 0 },
    P1: { total: 5, completed: 1, rate: 20 },
    P2: { total: 8, completed: 3, rate: 37.5 },
    P3: { total: 12, completed: 5, rate: 41.7 },
  }

  const p0Tasks = [
    { key: '1', priority: 'P0', scenario: 'P0-3', issue: '广告全部暂停', sku: '全店', action: '激活Top10广告', deadline: '24小时内', status: '待执行' },
    { key: '2', priority: 'P0', scenario: 'P0-1', issue: 'A类RED+低转化', sku: 'HAA240-10', action: '降价8% + 赠品', deadline: '24小时内', status: '待执行' },
    { key: '3', priority: 'P0', scenario: 'P0-4', issue: '金额骤降58%', sku: '全店', action: '诊断原因', deadline: '24小时内', status: '进行中' },
  ]

  const p1Tasks = [
    { key: '1', priority: 'P1', scenario: 'P1-1', issue: 'A类GREEN+高转化', sku: 'HAA132-01', action: '提价3-5%测试', deadline: '3天内', status: '待执行' },
    { key: '2', priority: 'P1', scenario: 'P1-2', issue: '漏斗瓶颈（浏览→加购）', sku: 'HAA240-10', action: '优化主图+标题', deadline: '3天内', status: '待执行' },
  ]

  // 策略执行率饼图
  const executionRateOption = {
    title: { text: '策略执行率', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [
      {
        name: '执行率',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: 'bold' },
        },
        labelLine: { show: false },
        data: [
          { value: 30, name: '已完成', itemStyle: { color: '#52c41a' } },
          { value: 70, name: '待执行', itemStyle: { color: '#d9d9d9' } },
        ],
      },
    ],
  }

  // 优先级分布
  const priorityDistOption = {
    title: { text: '策略优先级分布' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['P0', 'P1', 'P2', 'P3'] },
    yAxis: { type: 'value', name: '任务数' },
    series: [
      {
        name: '任务数',
        type: 'bar',
        data: [
          { value: strategySummary.P0.total, itemStyle: { color: '#ff4d4f' } },
          { value: strategySummary.P1.total, itemStyle: { color: '#faad14' } },
          { value: strategySummary.P2.total, itemStyle: { color: '#1890ff' } },
          { value: strategySummary.P3.total, itemStyle: { color: '#8c8c8c' } },
        ],
        label: {
          show: true,
          position: 'top',
        },
      },
    ],
  }

  const columns = [
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (pri: string) => {
      const colors: any = { P0: 'red', P1: 'orange', P2: 'blue', P3: 'default' }
      return <Tag color={colors[pri]}>{pri}</Tag>
    }},
    { title: '场景', dataIndex: 'scenario', key: 'scenario' },
    { title: '问题', dataIndex: 'issue', key: 'issue', width: 200 },
    { title: 'SKU', dataIndex: 'sku', key: 'sku' },
    { title: '行动', dataIndex: 'action', key: 'action', width: 200 },
    { title: '时限', dataIndex: 'deadline', key: 'deadline' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => {
      const colors: any = { '待执行': 'red', '进行中': 'orange', '已完成': 'green' }
      return <Tag color={colors[status]}>{status}</Tag>
    }},
  ]

  return (
    <div>
      {/* 策略统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="🔴 P0 紧急（24h内）"
              value={strategySummary.P0.total}
              suffix="条"
              valueStyle={{ color: '#ff4d4f' }}
            />
            <Progress percent={strategySummary.P0.rate} size="small" status="exception" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="🟡 P1 重要（3天内）"
              value={strategySummary.P1.total}
              suffix="条"
              valueStyle={{ color: '#faad14' }}
            />
            <Progress percent={strategySummary.P1.rate} size="small" strokeColor="#faad14" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="🔵 P2 优化（7天内）"
              value={strategySummary.P2.total}
              suffix="条"
              valueStyle={{ color: '#1890ff' }}
            />
            <Progress percent={strategySummary.P2.rate} size="small" strokeColor="#1890ff" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="⚪ P3 常规（30天内）"
              value={strategySummary.P3.total}
              suffix="条"
              valueStyle={{ color: '#8c8c8c' }}
            />
            <Progress percent={strategySummary.P3.rate} size="small" strokeColor="#8c8c8c" />
          </Card>
        </Col>
      </Row>

      {/* 策略分布图 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <ReactECharts option={executionRateOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <ReactECharts option={priorityDistOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      {/* P0 任务清单 */}
      <Card title="🔴 P0 紧急任务（24小时内执行）" style={{ marginBottom: 16 }}>
        <Table
          dataSource={p0Tasks}
          columns={columns}
          pagination={false}
          size="small"
        />
      </Card>

      {/* P1 任务清单 */}
      <Card title="🟡 P1 重要任务（3天内执行）">
        <Table
          dataSource={p1Tasks}
          columns={columns}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
