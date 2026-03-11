import { Card, Row, Col, Statistic, Table, Tag, Alert, Progress, Skeleton } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, ReloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import type { EChartsOption } from 'echarts'

// ==================== 类型定义 ====================
interface KPIMetric {
  title: string
  value: number
  unit?: string
  prefix?: string
  suffix?: string
  trend?: number
  trendLabel?: string
  status: 'success' | 'warning' | 'error' | 'normal'
}

interface AlertItem {
  id: number
  type: 'error' | 'warning' | 'info'
  message: string
  priority: string
  timestamp: string
}

interface StrategyTask {
  scenario: string
  issue: string
  sku: string
  action: string
  deadline: string
  status: '待执行' | '进行中' | '已完成'
}

// ==================== API 调用 ====================
const fetchDashboardData = async () => {
  const response = await fetch('http://localhost:5000/api/dashboard/overview')
  if (!response.ok) throw new Error('获取数据失败')
  return response.json()
}

// ==================== KPI 卡片组件 ====================
function KPICard({ metric, loading }: { metric: KPIMetric; loading: boolean }) {
  if (loading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 2 }} />
      </Card>
    )
  }

  const getStatusColor = (status: string) => {
    const colors = {
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      normal: '#1890ff'
    }
    return colors[status] || colors.normal
  }

  const formatValue = (value: number, unit?: string) => {
    if (unit === '₽') {
      return value.toLocaleString('ru-RU')
    }
    return value.toLocaleString()
  }

  return (
    <Card 
      hoverable
      style={{ 
        borderTop: `3px solid ${getStatusColor(metric.status)}`,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
      bodyStyle={{ padding: '20px' }}
    >
      <Statistic
        title={<span style={{ fontSize: '14px', color: '#8c8c8c' }}>{metric.title}</span>}
        value={metric.value}
        prefix={metric.prefix}
        suffix={metric.unit}
        valueStyle={{ 
          fontSize: '32px', 
          fontWeight: 700,
          color: getStatusColor(metric.status),
          fontFamily: 'SFMono-Regular, Consolas, monospace'
        }}
        formatter={(value) => formatValue(Number(value), metric.unit)}
      />
      
      {metric.trend !== undefined && (
        <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center' }}>
          <Tag 
            color={metric.trend >= 0 ? 'green' : 'red'}
            icon={metric.trend >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
          >
            {metric.trend >= 0 ? '+' : ''}{metric.trend.toFixed(1)}%
          </Tag>
          <span style={{ fontSize: '12px', color: '#8c8c8c', marginLeft: '8px' }}>
            {metric.trendLabel || '较上周'}
          </span>
        </div>
      )}
    </Card>
  )
}

// ==================== 订单趋势图表 ====================
function OrderTrendChart({ data, loading }: { data: any; loading: boolean }) {
  const option: EChartsOption = {
    title: {
      text: '📈 订单趋势（7天）',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#262626'
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#d9d9d9',
      borderWidth: 1,
      textStyle: {
        color: '#262626'
      },
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: '#1890ff',
          width: 1,
          type: 'dashed'
        }
      }
    },
    legend: {
      data: ['YunElite', 'ALORA'],
      top: 40,
      itemGap: 20,
      textStyle: {
        fontSize: 12,
        color: '#595959'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 80,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data?.dates || [],
      axisLine: {
        lineStyle: {
          color: '#d9d9d9'
        }
      },
      axisLabel: {
        color: '#595959',
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      name: '订单数',
      nameTextStyle: {
        color: '#8c8c8c',
        fontSize: 12
      },
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: '#595959',
        fontSize: 12
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: 'YunElite',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: data?.YunElite || [],
        itemStyle: {
          color: '#1890ff'
        },
        lineStyle: {
          width: 3,
          color: '#1890ff'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
            ]
          }
        }
      },
      {
        name: 'ALORA',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: data?.ALORA || [],
        itemStyle: {
          color: '#52c41a'
        },
        lineStyle: {
          width: 3,
          color: '#52c41a'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(82, 196, 26, 0.3)' },
              { offset: 1, color: 'rgba(82, 196, 26, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  return (
    <Card 
      style={{ height: '100%' }}
      bodyStyle={{ padding: '24px', height: '100%' }}
      extra={
        <a onClick={() => window.location.reload()}>
          <ReloadOutlined /> 刷新
        </a>
      }
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : (
        <ReactECharts 
          option={option} 
          style={{ height: '350px', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      )}
    </Card>
  )
}

// ==================== 店铺健康度雷达图 ====================
function ShopHealthRadar({ data, loading }: { data: any; loading: boolean }) {
  const option: EChartsOption = {
    title: {
      text: '🏪 店铺健康度',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
        color: '#262626'
      }
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#d9d9d9',
      borderWidth: 1
    },
    legend: {
      data: ['YunElite', 'ALORA'],
      top: 40,
      itemGap: 20
    },
    radar: {
      indicator: [
        { name: '商品评分', max: 100 },
        { name: '发货准时率', max: 100 },
        { name: '价格竞争力', max: 100 },
        { name: '库存健康度', max: 100 },
        { name: '广告效率', max: 100 }
      ],
      center: ['50%', '60%'],
      radius: '60%',
      axisName: {
        color: '#595959',
        fontSize: 12
      },
      splitArea: {
        areaStyle: {
          color: ['#fff', '#fafafa']
        }
      },
      axisLine: {
        lineStyle: {
          color: '#d9d9d9'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#d9d9d9'
        }
      }
    },
    series: [
      {
        name: '健康度指标',
        type: 'radar',
        data: [
          {
            value: [85, 100, 46, 78, 30],
            name: 'YunElite',
            itemStyle: {
              color: '#1890ff'
            },
            areaStyle: {
              color: 'rgba(24, 144, 255, 0.3)'
            }
          },
          {
            value: [82, 100, 49, 75, 28],
            name: 'ALORA',
            itemStyle: {
              color: '#52c41a'
            },
            areaStyle: {
              color: 'rgba(82, 196, 26, 0.3)'
            }
          }
        ]
      }
    ]
  }

  return (
    <Card 
      style={{ height: '100%' }}
      bodyStyle={{ padding: '24px', height: '100%' }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : (
        <ReactECharts 
          option={option} 
          style={{ height: '350px', width: '100%' }}
        />
      )}
    </Card>
  )
}

// ==================== P0 任务列表 ====================
function P0TaskList({ tasks, loading }: { tasks: StrategyTask[]; loading: boolean }) {
  const columns = [
    {
      title: 'SKU',
      dataIndex: 'sku',
      key: 'sku',
      width: 120,
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '问题',
      dataIndex: 'issue',
      key: 'issue',
      ellipsis: true,
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>
    },
    {
      title: '行动',
      dataIndex: 'action',
      key: 'action',
      ellipsis: true
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors: Record<string, string> = {
          '待执行': 'red',
          '进行中': 'orange',
          '已完成': 'green'
        }
        return <Tag color={colors[status]}>{status}</Tag>
      }
    }
  ]

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span style={{ fontSize: '16px', fontWeight: 600 }}>🔴 P0 紧急任务</span>
          <Tag color="red" style={{ marginLeft: '8px' }}>
            {tasks.length} 条
          </Tag>
        </div>
      }
      style={{ height: '100%' }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 3 }} />
      ) : (
        <Table
          dataSource={tasks}
          columns={columns}
          pagination={false}
          size="small"
          scroll={{ y: 240 }}
          rowClassName={(record, index) => 
            index % 2 === 0 ? 'table-row-light' : 'table-row-dark'
          }
        />
      )}
    </Card>
  )
}

// ==================== 异常告警列表 ====================
function AlertList({ alerts, loading }: { alerts: AlertItem[]; loading: boolean }) {
  const getAlertStyle = (type: string) => {
    const styles = {
      error: { background: '#fff2f0', borderLeft: '4px solid #ff4d4f' },
      warning: { background: '#fffbe6', borderLeft: '4px solid #faad14' },
      info: { background: '#e6f7ff', borderLeft: '4px solid #1890ff' }
    }
    return styles[type] || styles.info
  }

  const getPriorityTag = (priority: string) => {
    const colors: Record<string, string> = {
      'P0': 'red',
      'P1': 'orange',
      'P2': 'blue',
      'P3': 'default'
    }
    return <Tag color={colors[priority]}>{priority}</Tag>
  }

  return (
    <Card 
      title={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span style={{ fontSize: '16px', fontWeight: 600 }}>⚠️ 异常告警</span>
          <Tag color="orange" style={{ marginLeft: '8px' }}>
            {alerts.length} 条
          </Tag>
        </div>
      }
      style={{ height: '100%' }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 3 }} />
      ) : (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {alerts.map((alert) => (
            <div
              key={alert.id}
              style={{
                ...getAlertStyle(alert.type),
                padding: '12px 16px',
                marginBottom: '12px',
                borderRadius: '4px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                  {alert.message}
                </div>
                <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                  {alert.timestamp}
                </div>
              </div>
              {getPriorityTag(alert.priority)}
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

// ==================== 主组件 ====================
export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0)

  // 获取仪表盘数据
  const { data: dashboardData, isLoading, refetch } = useQuery({
    queryKey: ['dashboard', refreshKey],
    queryFn: fetchDashboardData,
    refetchInterval: 60000, // 每分钟刷新
  })

  // 手动刷新
  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1)
    refetch()
  }

  // KPI 数据
  const kpiMetrics: KPIMetric[] = [
    {
      title: '总订单数（7天）',
      value: dashboardData?.data?.kpi_metrics?.orders_7d?.total || 276,
      unit: '单',
      trend: 12.5,
      status: 'success'
    },
    {
      title: '总销售额（7天）',
      value: dashboardData?.data?.kpi_metrics?.revenue_7d?.total || 96913,
      prefix: '₽',
      trend: -3.2,
      status: 'warning'
    },
    {
      title: '平均客单价',
      value: dashboardData?.data?.kpi_metrics?.avg_order_value || 404,
      prefix: '₽',
      trend: -8.1,
      status: 'error'
    },
    {
      title: '转化率',
      value: (dashboardData?.data?.kpi_metrics?.conversion_rate || 0.001) * 100,
      unit: '%',
      trend: -15.0,
      status: 'error'
    },
    {
      title: '店铺评分',
      value: dashboardData?.data?.shop_health?.YunElite?.rating || 4.8,
      trend: 0.2,
      status: 'success'
    }
  ]

  // P0 任务数据
  const p0Tasks: StrategyTask[] = [
    {
      scenario: 'P0-3',
      issue: '广告全部暂停',
      sku: '全店',
      action: '激活Top10广告',
      deadline: '24小时内',
      status: '待执行'
    },
    {
      scenario: 'P0-1',
      issue: 'A类RED+低转化',
      sku: 'HAA240-10',
      action: '降价8% + 赠品',
      deadline: '24小时内',
      status: '待执行'
    },
    {
      scenario: 'P0-4',
      issue: '金额骤降58%',
      sku: '全店',
      action: '诊断原因',
      deadline: '24小时内',
      status: '进行中'
    }
  ]

  // 异常告警数据
  const alerts: AlertItem[] = dashboardData?.data?.alerts || [
    { id: 1, type: 'error', message: '广告全部暂停', priority: 'P0', timestamp: '2分钟前' },
    { id: 2, type: 'warning', message: '金额骤降 58%', priority: 'P1', timestamp: '15分钟前' },
    { id: 3, type: 'error', message: 'YunYi 数据失败率 16.7%', priority: 'P1', timestamp: '1小时前' }
  ]

  // 订单趋势数据
  const orderTrendData = {
    dates: ['03-02', '03-03', '03-04', '03-05', '03-06', '03-07', '03-08'],
    YunElite: [47, 40, 45, 23, 27, 24, 22],
    ALORA: [12, 15, 11, 8, 10, 9, 9]
  }

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 页面头部 */}
      <div style={{ 
        background: '#fff', 
        padding: '16px 24px', 
        marginBottom: '24px',
        borderRadius: '8px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
            📊 运营概览
          </h1>
          <p style={{ margin: '8px 0 0 0', color: '#8c8c8c', fontSize: '14px' }}>
            最后更新: {new Date().toLocaleString('zh-CN')}
          </p>
        </div>
        <a onClick={handleRefresh} style={{ fontSize: '14px' }}>
          <ReloadOutlined /> 刷新数据
        </a>
      </div>

      {/* KPI 卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        {kpiMetrics.map((metric, index) => (
          <Col xs={24} sm={12} md={8} lg={4} xl={4.8} key={index}>
            <KPICard metric={metric} loading={isLoading} />
          </Col>
        ))}
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} lg={14}>
          <OrderTrendChart data={orderTrendData} loading={isLoading} />
        </Col>
        <Col xs={24} lg={10}>
          <ShopHealthRadar data={dashboardData?.data?.shop_health} loading={isLoading} />
        </Col>
      </Row>

      {/* 任务和告警 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <P0TaskList tasks={p0Tasks} loading={isLoading} />
        </Col>
        <Col xs={24} lg={12}>
          <AlertList alerts={alerts} loading={isLoading} />
        </Col>
      </Row>

      {/* 自定义样式 */}
      <style>{`
        .table-row-light {
          background: #fafafa;
        }
        .table-row-dark {
          background: #fff;
        }
        .ant-card {
          box-shadow: 0 1px 2px rgba(0,0,0,0.03);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .ant-card:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .ant-statistic-content-value {
          font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }
      `}</style>
    </div>
  )
}
