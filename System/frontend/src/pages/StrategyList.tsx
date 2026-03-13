import { Card, Row, Col, Table, Tag, Button, Select, Space, Statistic, Badge, Modal, Divider, Progress, Tooltip, message } from 'antd'
import { CheckCircleOutlined, WarningOutlined, ClockCircleOutlined, BulbOutlined, UserOutlined, CalendarOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { strategyApi } from '../services/api'
import type { StrategyTask } from '../types'
import { strategyTypeLabels, statusLabels, sourcePageLabels } from '../utils/labels'
import { displayOrDash, formatInteger, formatRate } from '../utils/format'

export default function StrategyList() {
  const [filterPriority, setFilterPriority] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterType, setFilterType] = useState<string>('all')
  const [selectedTask, setSelectedTask] = useState<StrategyTask | null>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  const queryClient = useQueryClient()
  const updateStatusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: number; status: string }) => strategyApi.updateTaskStatus(taskId, { status, assignedTo: 'strategy_ui' }),
    onSuccess: () => {
      message.success('状态已更新并写库')
      queryClient.invalidateQueries({ queryKey: ['strategy-list'] })
      queryClient.invalidateQueries({ queryKey: ['decision-preview'] })
    },
    onError: (e: any) => message.error(`状态更新失败: ${e.message}`),
  })

  // 获取数据 - 调用真实后端API（失败时使用 mock 数据）
  const { data: taskList, isLoading } = useQuery<StrategyTask[]>({
    queryKey: ['strategy-list', filterPriority, filterStatus, filterType],
    queryFn: async (): Promise<StrategyTask[]> => {
      const response = await strategyApi.getStrategyList()
      return response?.tasks || []
    },
    staleTime: 5 * 60 * 1000, // 5分钟内数据视为新鲜
  })

  // 统计数据
  const stats = {
    total: taskList?.length || 0,
    pending: taskList?.filter(t => t.status === 'pending').length || 0,
    inProgress: taskList?.filter(t => t.status === 'in_progress').length || 0,
    completed: taskList?.filter(t => t.status === 'completed').length || 0,
    p0Tasks: taskList?.filter(t => t.priority === 'P0').length || 0,
    p1Tasks: taskList?.filter(t => t.priority === 'P1').length || 0
  }

  // 优先级分布图
  const priorityDistributionOption = {
    title: { text: '优先级分布', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { value: taskList?.filter(t => t.priority === 'P0').length || 0, name: 'P0', itemStyle: { color: '#f5222d' } },
          { value: taskList?.filter(t => t.priority === 'P1').length || 0, name: 'P1', itemStyle: { color: '#fa8c16' } },
          { value: taskList?.filter(t => t.priority === 'P2').length || 0, name: 'P2', itemStyle: { color: '#faad14' } },
          { value: taskList?.filter(t => t.priority === 'P3').length || 0, name: 'P3', itemStyle: { color: '#52c41a' } }
        ]
      }
    ]
  }

  // 策略类型分布
  const typeDistributionOption = {
    title: { text: '策略类型分布', left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: ['定价策略', '库存策略', '转化优化', '广告优化', '风控策略']
    },
    yAxis: { type: 'value', name: '任务数' },
    series: [
      {
        type: 'bar',
        data: [
          taskList?.filter(t => t.strategyType === 'pricing').length || 0,
          taskList?.filter(t => t.strategyType === 'inventory').length || 0,
          taskList?.filter(t => t.strategyType === 'conversion').length || 0,
          taskList?.filter(t => t.strategyType === 'ads').length || 0,
          taskList?.filter(t => t.strategyType === 'risk_control').length || 0
        ],
        itemStyle: { color: '#1890ff' },
        label: { show: true, position: 'top' }
      }
    ]
  }

  // 任务状态分布
  const statusDistributionOption = {
    title: { text: '任务状态分布', left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { value: stats.pending, name: '待处理', itemStyle: { color: '#8c8c8c' } },
          { value: stats.inProgress, name: '进行中', itemStyle: { color: '#1890ff' } },
          { value: stats.completed, name: '已完成', itemStyle: { color: '#52c41a' } }
        ]
      }
    ]
  }

  // 表格列定义
  const columns = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      fixed: 'left' as const,
      width: 80,
      sorter: (a: StrategyTask, b: StrategyTask) => {
        const priorityOrder: Record<string, number> = { P0: 4, P1: 3, P2: 2, P3: 1 }
        return priorityOrder[a.priority] - priorityOrder[b.priority]
      },
      render: (val: string) => {
        const colorMap: Record<string, string> = {
          P0: '#f5222d',
          P1: '#fa8c16',
          P2: '#faad14',
          P3: '#52c41a'
        }
        return <Badge color={colorMap[val]} text={val} />
      }
    },
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120
    },
    {
      title: '策略类型',
      dataIndex: 'strategyType',
      key: 'strategyType',
      width: 120,
      render: (val: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          pricing: { color: 'blue', text: '定价策略' },
          inventory: { color: 'cyan', text: '库存策略' },
          conversion: { color: 'green', text: '转化优化' },
          ads: { color: 'purple', text: '广告优化' },
          risk_control: { color: 'red', text: '风控策略' }
        }
        const { color, text } = typeMap[val] || { color: 'default', text: strategyTypeLabels[val] || '其他策略' }
        return <Tag color={color}>{text}</Tag>
      }
    },
    {
      title: '问题描述',
      dataIndex: 'issueSummary',
      key: 'issueSummary',
      width: 200,
      ellipsis: true,
      render: (text: string) => <Tooltip title={text}>{text}</Tooltip>
    },
    {
      title: '建议操作',
      dataIndex: 'recommendedAction',
      key: 'recommendedAction',
      width: 250,
      ellipsis: true,
      render: (text: string) => <Tooltip title={text}>{text}</Tooltip>
    },
    {
      title: '来源页面',
      dataIndex: 'sourcePage',
      key: 'sourcePage',
      width: 120,
      render: (v: string) => <Tag color="geekblue">{sourcePageLabels[v] || displayOrDash(v)}</Tag>
    },
    {
      title: '来源原因',
      dataIndex: 'sourceReason',
      key: 'sourceReason',
      width: 220,
      ellipsis: true,
      render: (v: string) => <Tooltip title={v}>{displayOrDash(v)}</Tooltip>
    },
    {
      title: '最近决策时间',
      dataIndex: 'lastDecisionAt',
      key: 'lastDecisionAt',
      width: 160,
      render: (v: string) => displayOrDash(v ? new Date(v).toLocaleString('zh-CN') : '—')
    },
    {
      title: '最近执行结果',
      dataIndex: 'lastExecution',
      key: 'lastExecution',
      width: 220,
      render: (v: any) => <Tooltip title={v?.resultSummary || '暂无执行记录'}>{displayOrDash(v?.resultSummary || '暂无执行记录')}</Tooltip>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val: string) => {
        const config: Record<string, { color: string; text: string; icon: any }> = {
          pending: { color: 'default', text: '待处理', icon: <ClockCircleOutlined /> },
          in_progress: { color: 'processing', text: '进行中', icon: <BulbOutlined /> },
          completed: { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
          cancelled: { color: 'error', text: '已取消', icon: <WarningOutlined /> }
        }
        const { color, text, icon } = config[val] || { color: 'default', text: statusLabels[val] || '未知状态', icon: null }
        return <Badge status={color as any} text={<Space>{icon}<span>{text}</span></Space>} />
      }
    },
    {
      title: '负责人',
      dataIndex: 'assignee',
      key: 'assignee',
      width: 100,
      render: (val?: string) => val ? (
        <Space>
          <UserOutlined />
          {val}
        </Space>
      ) : '-'
    },
    {
      title: '截止日期',
      dataIndex: 'dueDate',
      key: 'dueDate',
      width: 120,
      render: (val?: string) => val ? (
        <Space>
          <CalendarOutlined />
          {val}
        </Space>
      ) : '-'
    },
    {
      title: '影响力',
      dataIndex: 'impact',
      key: 'impact',
      width: 100,
      render: (val?: number) => val ? (
        <Progress
          percent={val * 10}
          size="small"
          format={percent => formatRate((percent || 0) / 10, 1)}
          strokeColor={val > 7 ? '#52c41a' : val > 5 ? '#faad14' : '#f5222d'}
        />
      ) : '-'
    },
    {
      title: '紧急度',
      dataIndex: 'urgency',
      key: 'urgency',
      width: 100,
      render: (val?: number) => val ? (
        <Progress
          percent={val * 10}
          size="small"
          format={percent => formatRate((percent || 0) / 10, 1)}
          strokeColor={val > 7 ? '#f5222d' : val > 5 ? '#faad14' : '#52c41a'}
        />
      ) : '-'
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      width: 120,
      render: (_: any, record: StrategyTask) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              loading={updateStatusMutation.isPending}
              onClick={() => {
                const taskId = Number(record.id)
                if (!Number.isFinite(taskId)) {
                  message.warning('任务ID无效，无法更新状态')
                  return
                }
                updateStatusMutation.mutate({ taskId, status: 'in_progress' })
              }}
            >
              开始
            </Button>
          )}
        </Space>
      )
    }
  ]

  // 查看详情
  const handleViewDetail = (task: StrategyTask) => {
    setSelectedTask(task)
    setDetailModalVisible(true)
  }

  // 过滤数据
  const filteredData = taskList?.filter(t => {
    const priorityMatch = filterPriority === 'all' || t.priority === filterPriority
    const statusMatch = filterStatus === 'all' || t.status === filterStatus
    const typeMatch = filterType === 'all' || t.strategyType === filterType
    return priorityMatch && statusMatch && typeMatch
  })

  return (
    <div style={{ padding: '24px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }}>
        📋 策略清单
      </h1>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总任务数"
              value={stats.total}
              prefix={<BulbOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="待处理"
              value={stats.pending}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#8c8c8c' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="进行中"
              value={stats.inProgress}
              prefix={<BulbOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已完成"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={8}>
          <Card>
            <ReactECharts option={priorityDistributionOption} style={{ height: '300px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <ReactECharts option={typeDistributionOption} style={{ height: '300px' }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <ReactECharts option={statusDistributionOption} style={{ height: '300px' }} />
          </Card>
        </Col>
      </Row>

      {/* 过滤器和表格 */}
      <Card
        title="策略任务列表"
        extra={
          <Space>
            <Select
              value={filterPriority}
              onChange={setFilterPriority}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部优先级</Select.Option>
              <Select.Option value="P0">P0</Select.Option>
              <Select.Option value="P1">P1</Select.Option>
              <Select.Option value="P2">P2</Select.Option>
              <Select.Option value="P3">P3</Select.Option>
            </Select>
            <Select
              value={filterStatus}
              onChange={setFilterStatus}
              style={{ width: 120 }}
            >
              <Select.Option value="all">全部状态</Select.Option>
              <Select.Option value="pending">待处理</Select.Option>
              <Select.Option value="in_progress">进行中</Select.Option>
              <Select.Option value="completed">已完成</Select.Option>
            </Select>
            <Select
              value={filterType}
              onChange={setFilterType}
              style={{ width: 140 }}
            >
              <Select.Option value="all">全部类型</Select.Option>
              <Select.Option value="pricing">定价策略</Select.Option>
              <Select.Option value="inventory">库存策略</Select.Option>
              <Select.Option value="conversion">转化优化</Select.Option>
              <Select.Option value="ads">广告优化</Select.Option>
              <Select.Option value="risk_control">风控策略</Select.Option>
            </Select>
            <Button type="primary" onClick={() => message.info('导出功能')}>
              导出报表
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={filteredData}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 1800 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${formatInteger(total)} 条`
          }}
        />
      </Card>

      {/* 详情模态框 */}
      <Modal
        title={`策略详情 - ${selectedTask?.sku}`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
          selectedTask?.status === 'pending' && (
            <Button key="start" type="primary" onClick={() => message.info('开始处理')}>
              开始处理
            </Button>
          )
        ]}
        width={800}
      >
        {selectedTask && (
          <div>
            <Row gutter={16}>
              <Col span={12}>
                <div><strong>SKU:</strong> {selectedTask.sku}</div>
              </Col>
              <Col span={12}>
                <div><strong>优先级:</strong> <Badge color={
                  selectedTask.priority === 'P0' ? '#f5222d' :
                  selectedTask.priority === 'P1' ? '#fa8c16' :
                  selectedTask.priority === 'P2' ? '#faad14' : '#52c41a'
                } text={selectedTask.priority} /></div>
              </Col>
            </Row>

            <Divider />

            <div><strong>问题描述:</strong></div>
            <p style={{ padding: '12px', background: '#f5f5f5', borderRadius: '4px', marginTop: '8px' }}>
              {selectedTask.issueSummary}
            </p>

            <div style={{ marginTop: '16px' }}><strong>建议操作:</strong></div>
            <p style={{ padding: '12px', background: '#e6f7ff', borderRadius: '4px', marginTop: '8px' }}>
              {selectedTask.recommendedAction}
            </p>

            <Divider />

            <Row gutter={16}>
              <Col span={12}>
                <div><strong>策略类型:</strong> {strategyTypeLabels[selectedTask.strategyType] || '其他策略'}</div>
              </Col>
              <Col span={12}>
                <div><strong>当前状态:</strong> {statusLabels[selectedTask.status] || selectedTask.status || '未知状态'}</div>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: '16px' }}>
              <Col span={12}>
                <div><strong>来源页面:</strong> {sourcePageLabels[(selectedTask as any).sourcePage] || displayOrDash((selectedTask as any).sourcePage)}</div>
              </Col>
              <Col span={12}>
                <div><strong>来源原因:</strong> {displayOrDash((selectedTask as any).sourceReason)}</div>
              </Col>
            </Row>

            <Row gutter={16} style={{ marginTop: '16px' }}>
              <Col span={12}>
                <div><strong>最近进入决策:</strong> {displayOrDash((selectedTask as any).lastDecisionAt ? new Date((selectedTask as any).lastDecisionAt).toLocaleString('zh-CN') : '—')}</div>
              </Col>
              <Col span={12}>
                <div><strong>最近执行结果:</strong> {displayOrDash((selectedTask as any).lastExecution?.resultSummary || '暂无执行记录')}</div>
              </Col>
            </Row>

            <Row gutter={16} style={{ marginTop: '16px' }}>
              <Col span={12}>
                <div><strong>负责人:</strong> {displayOrDash(selectedTask.assignee)}</div>
              </Col>
              <Col span={12}>
                <div><strong>截止日期:</strong> {displayOrDash(selectedTask.dueDate)}</div>
              </Col>
            </Row>

            <Row gutter={16} style={{ marginTop: '16px' }}>
              <Col span={12}>
                <div><strong>创建时间:</strong> {displayOrDash(selectedTask.createdAt)}</div>
              </Col>
              <Col span={12}>
                <div><strong>完成时间:</strong> {displayOrDash(selectedTask.completedAt)}</div>
              </Col>
            </Row>

            {selectedTask.observationMetrics && selectedTask.observationMetrics.length > 0 && (
              <>
                <Divider />
                <div><strong>观察指标:</strong></div>
                <div style={{ marginTop: '8px' }}>
                  {selectedTask.observationMetrics.map((metric, index) => (
                    <Tag key={index} color="blue">{metric}</Tag>
                  ))}
                </div>
              </>
            )}

            {selectedTask.impact && selectedTask.urgency && (
              <>
                <Divider />
                <Row gutter={16}>
                  <Col span={12}>
                    <div><strong>影响力评分:</strong></div>
                    <Progress
                      percent={selectedTask.impact * 10}
                      format={percent => formatRate((percent || 0) / 10, 1)}
                      strokeColor={selectedTask.impact > 7 ? '#52c41a' : selectedTask.impact > 5 ? '#faad14' : '#f5222d'}
                    />
                  </Col>
                  <Col span={12}>
                    <div><strong>紧急度评分:</strong></div>
                    <Progress
                      percent={selectedTask.urgency * 10}
                      format={percent => formatRate((percent || 0) / 10, 1)}
                      strokeColor={selectedTask.urgency > 7 ? '#f5222d' : selectedTask.urgency > 5 ? '#faad14' : '#52c41a'}
                    />
                  </Col>
                </Row>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
