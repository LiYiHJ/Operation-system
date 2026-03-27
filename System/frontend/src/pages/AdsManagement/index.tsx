import { Row, Col, Card, Table, Tag, Statistic, Alert, Progress } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import LazyEChart from '../../components/charts/LazyEChart'

export default function AdsManagement() {
  const adsSummary = {
    YunElite: { total: 62, active: 0, paused: 62, spend: 0, revenue: 0, roas: 0 },
    ALORA: { total: 16, active: 0, paused: 16, spend: 0, revenue: 0, roas: 0 },
  }

  const adsList = [
    { key: '1', id: 'CAMP-001', name: 'S【HAA244-01-Y1】四重挤水迷你小拖把', status: '暂停', placement: '搜索和分类页', budget: 6000, strategy: 'MAX_CLICKS', roas: 0 },
    { key: '2', id: 'CAMP-002', name: '二月精选：已精选出最适合推广的商品...', status: '暂停', placement: '顶部推广位', budget: 2000, strategy: 'TARGET_BIDS', roas: 0 },
    { key: '3', id: 'CAMP-003', name: '广告活动3', status: '暂停', placement: '搜索和分类页', budget: 4000, strategy: 'TOP_MAX_CLICKS', roas: 0 },
  ]

  // 广告花费趋势
  const spendTrendOption = {
    title: { text: '广告花费趋势（7天）' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['03-02', '03-03', '03-04', '03-05', '03-06', '03-07', '03-08'] },
    yAxis: { type: 'value', name: '花费 (₽)' },
    series: [
      {
        name: '广告花费',
        type: 'line',
        data: [0, 0, 0, 0, 0, 0, 0],
      },
    ],
  }

  // ROAS 分布
  const roasDistOption = {
    title: { text: 'ROAS 分布（最近30天）' },
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        name: 'ROAS 范围',
        type: 'pie',
        radius: '50%',
        data: [
          { value: 0, name: '无数据（广告全部暂停）', itemStyle: { color: '#d9d9d9' } },
        ],
      },
    ],
  }

  const adsColumns = [
    { title: '活动ID', dataIndex: 'id', key: 'id' },
    { title: '活动名称', dataIndex: 'name', key: 'name', width: 300 },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={status === '运行中' ? 'green' : 'red'}>{status}</Tag>
    ) },
    { title: '投放位置', dataIndex: 'placement', key: 'placement' },
    { title: '周预算(₽)', dataIndex: 'budget', key: 'budget' },
    { title: '出价策略', dataIndex: 'strategy', key: 'strategy', render: (strategy: string) => {
      const strategyMap: any = {
        'MAX_CLICKS': '最大化点击',
        'TARGET_BIDS': '目标出价',
        'TOP_MAX_CLICKS': '顶部最大化点击',
      }
      return strategyMap[strategy] || strategy
    }},
    { title: 'ROAS', dataIndex: 'roas', key: 'roas', render: (roas: number) => (
      <Tag color={roas === 0 ? 'default' : roas > 3 ? 'green' : 'red'}>{roas === 0 ? '无数据' : roas.toFixed(2)}</Tag>
    ) },
  ]

  return (
    <div>
      {/* 严重告警 */}
      <Alert
        message="⚠️ 广告全部暂停"
        description="YunElite 和 ALORA 的所有广告活动均已暂停，建议立即激活核心产品的广告！"
        type="error"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 广告统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="YunElite 广告活动"
              value={adsSummary.YunElite.total}
              suffix="个"
            />
            <p>
              <Tag color="red">暂停: {adsSummary.YunElite.paused}</Tag>
              <Tag color="green">运行: {adsSummary.YunElite.active}</Tag>
            </p>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="ALORA 广告活动"
              value={adsSummary.ALORA.total}
              suffix="个"
            />
            <p>
              <Tag color="red">暂停: {adsSummary.ALORA.paused}</Tag>
              <Tag color="green">运行: {adsSummary.ALORA.active}</Tag>
            </p>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总广告花费（7天）"
              value={adsSummary.YunElite.spend + adsSummary.ALORA.spend}
              prefix="₽"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总 ROAS"
              value={0}
              suffix="（无数据）"
            />
          </Card>
        </Col>
      </Row>

      {/* 广告趋势图 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <LazyEChart option={spendTrendOption} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <LazyEChart option={roasDistOption} style={{ height: 300 }} />
          </Card>
        </Col>
      </Row>

      {/* 广告活动列表 */}
      <Card title="📢 广告活动列表">
        <Table
          dataSource={adsList}
          columns={adsColumns}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
