import { useMemo, useState } from 'react'
import {
  Card, Row, Col, Form, InputNumber, Select, Button, Space, Divider, Table, Tag, Typography, Alert, Tabs, Statistic, List, message, Collapse
} from 'antd'
import { CalculatorOutlined, BranchesOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { profitApi } from '../services/api'
import { formatCurrency, formatPercent } from '../utils/format'
import { OpsConclusion, OpsPageHeader, OpsRiskTag } from '../components/ops/ProductSection'

const { Title, Text } = Typography

type LayeredParams = {
  platform_auto: Record<string, number>
  shop_default: Record<string, number>
  sku_override: Record<string, number>
  simulation_override: Record<string, number>
}

export default function ProfitCalculator() {
  const [form] = Form.useForm()
  const [profile, setProfile] = useState('ozon_daily_profit')
  const [mode, setMode] = useState('current')
  const [layers, setLayers] = useState<LayeredParams>({
    platform_auto: { variable_rate_total: 0.31, fixed_cost_total: 72 },
    shop_default: { variable_rate_total: 0.29, fixed_cost_total: 69 },
    sku_override: {},
    simulation_override: {},
  })
  const [scenarios, setScenarios] = useState<any[]>([
    { key: 'base', name: '日常场景', sale_price: 119, list_price: 129 },
    { key: 'campaign', name: '平台活动场景', sale_price: 109, list_price: 129 },
    { key: 'promo', name: '自建促销场景', sale_price: 99, list_price: 129 },
  ])
  const [requestPayload, setRequestPayload] = useState<any>(() => ({
    mode: 'current',
    targetValue: 0,
    salePrice: 119,
    listPrice: 129,
    variableRateTotal: 0.31,
    fixedCostTotal: 72,
    algorithmProfile: 'ozon_daily_profit',
    layeredParams: {
      platform_auto: { variable_rate_total: 0.31, fixed_cost_total: 72 },
      shop_default: { variable_rate_total: 0.29, fixed_cost_total: 69 },
      sku_override: {},
      simulation_override: {},
    },
    scenarios: [
      { name: '日常场景', layered_params: { simulation_override: { sale_price: 119, list_price: 129 } } },
      { name: '平台活动场景', layered_params: { simulation_override: { sale_price: 109, list_price: 129 } } },
      { name: '自建促销场景', layered_params: { simulation_override: { sale_price: 99, list_price: 129 } } },
    ],
  }))

  const { data: profileData } = useQuery({
    queryKey: ['profit-profiles'],
    queryFn: () => profitApi.getProfiles(),
    staleTime: 5 * 60 * 1000,
  })

  const { data: solveData, isFetching } = useQuery({
    queryKey: ['profit-solve', requestPayload],
    queryFn: () => profitApi.solve(requestPayload),
    enabled: !!requestPayload,
  })

  const { data: snapshotData, refetch: refetchSnapshots } = useQuery({
    queryKey: ['profit-snapshots'],
    queryFn: () => profitApi.getSnapshots({ shopId: 1, limit: 10 }),
  })

  const { data: templateData, refetch: refetchTemplates } = useQuery({
    queryKey: ['profit-templates'],
    queryFn: () => profitApi.getTemplates({ shopId: 1, limit: 10 }),
  })

  const saveSnapshotMutation = useMutation({
    mutationFn: (payload: any) => profitApi.saveSnapshot(payload),
    onSuccess: () => {
      message.success('利润快照已保存')
      refetchSnapshots()
    },
    onError: (error: any) => message.error(`保存快照失败: ${error.message}`),
  })

  const saveTemplateMutation = useMutation({
    mutationFn: (payload: any) => profitApi.saveTemplate(payload),
    onSuccess: () => {
      message.success('利润模板已保存')
      refetchTemplates()
    },
    onError: (error: any) => message.error(`保存模板失败: ${error.message}`),
  })

  const onCalculate = async () => {
    const values = await form.validateFields()
    const payload = {
      mode,
      targetValue: values.targetValue || 0,
      salePrice: values.salePrice,
      listPrice: values.listPrice,
      variableRateTotal: values.variableRateTotal,
      fixedCostTotal: values.fixedCostTotal,
      algorithmProfile: profile,
      layeredParams: layers,
      scenarios: scenarios.map((s) => ({
        name: s.name,
        layered_params: { simulation_override: { sale_price: s.sale_price, list_price: s.list_price } }
      })),
    }
    setRequestPayload(payload)
  }

  const scenarioColumns = [
    { title: '场景', dataIndex: 'name', key: 'name' },
    {
      title: '售价',
      dataIndex: 'sale_price',
      key: 'sale_price',
      render: (v: number, record: any, idx: number) => (
        <InputNumber value={v} min={1} onChange={(val) => {
          const next = [...scenarios]
          next[idx].sale_price = Number(val || 0)
          setScenarios(next)
        }} />
      )
    },
  ]

  const fixedColumns = [
    { title: '成本项', dataIndex: 'label', width: 170, ellipsis: true },
    {
      title: '原价',
      dataIndex: 'list_price',
      key: 'list_price',
      render: (v: number, record: any, idx: number) => (
        <InputNumber value={v} min={1} onChange={(val) => {
          const next = [...scenarios]
          next[idx].list_price = Number(val || 0)
          setScenarios(next)
        }} />
      )
    },
  ]

  const scenarioResultColumns = [
    { title: '场景', dataIndex: 'name', key: 'name' },
    { title: '净利润', dataIndex: ['result', 'net_profit'], key: 'net_profit' },
    {
      title: '净利率',
      dataIndex: ['result', 'net_margin'],
      key: 'net_margin',
      render: (v: number) => `${(Number(v || 0) * 100).toFixed(2)}%`
    },
    {
      title: '盈亏状态',
      dataIndex: ['result', 'is_loss'],
      key: 'is_loss',
      render: (v: boolean) => <Tag color={v ? 'red' : 'green'}>{v ? '亏损' : '盈利'}</Tag>
    }
  ]

  const current = solveData?.current

  const sourceStatusRows = [
    { variable: 'variable_rate_total', value: requestPayload?.variableRateTotal || 0, source: layers.simulation_override.variable_rate_total != null ? 'simulation' : layers.sku_override.variable_rate_total != null ? 'sku' : layers.shop_default.variable_rate_total != null ? 'shop' : 'platform' },
    { variable: 'fixed_cost_total', value: requestPayload?.fixedCostTotal || 0, source: layers.simulation_override.fixed_cost_total != null ? 'simulation' : layers.sku_override.fixed_cost_total != null ? 'sku' : layers.shop_default.fixed_cost_total != null ? 'shop' : 'platform' },
    { variable: 'sale_price', value: requestPayload?.salePrice || 0, source: 'simulation' },
    { variable: 'list_price', value: requestPayload?.listPrice || 0, source: 'platform' },
  ]

  const profitBreakdown = [
    { item: '预计收入', value: requestPayload?.salePrice || 0 },
    { item: '变量成本', value: (requestPayload?.salePrice || 0) * (requestPayload?.variableRateTotal || 0) },
    { item: '固定成本', value: requestPayload?.fixedCostTotal || 0 },
    { item: '净利润', value: current?.net_profit || 0 },
  ]

  const scenarioInterpretation = (solveData?.scenario_results || []).map((r: any) => ({
    name: r.name,
    note: r.result?.is_loss ? '该场景亏损，建议提高售价或降低费率/成本' : r.result?.net_margin > 0.2 ? '高利润场景，可优先执行' : '中性场景，需结合流量目标判断'
  }))

  const riskScan = useMemo(() => solveData?.riskScan || [], [solveData])

  const handleSaveSnapshot = () => {
    if (!requestPayload || !solveData) {
      message.warning('请先运行算法后再保存快照')
      return
    }
    saveSnapshotMutation.mutate({
      shopId: 1,
      snapshotName: `${profile}-snapshot-${Date.now()}`,
      algorithmProfile: profile,
      payload: requestPayload,
      result: solveData,
      operator: 'profit_ui',
    })
  }

  const handleSaveTemplate = () => {
    saveTemplateMutation.mutate({
      shopId: 1,
      templateName: `${profile}-template-${Date.now()}`,
      algorithmProfile: profile,
      layeredParams: layers,
      scenarios,
      operator: 'profit_ui',
    })
  }

  return (
    <div style={{ padding: 20 }}>
      <OpsPageHeader title="💹 利润决策工作台" subtitle="先看最佳建议，再查看参数来源、风险扫描与快照模板。" />
      <OpsConclusion
        title="当前利润结论"
        desc={`净利润 ${formatCurrency(current?.net_profit || 0)}，净利率 ${formatPercent(current?.net_margin || 0, 1, true)}，建议售价 ${formatCurrency(solveData?.suggested_price || 0)}。`}
        level={(current?.is_loss ? 'error' : 'success') as any}
      />
      <div style={{ height: 10 }} />

      <Row gutter={[12, 12]}>
        <Col span={24}>
          <Card size="small" title={<span><BranchesOutlined /> 算法模式与参数来源分层</span>} bodyStyle={{ padding: 16 }}>
            <Row gutter={16}>
              <Col xs={24} lg={8}>
                <Text strong>算法 Profile</Text>
                <Select
                  value={profile}
                  onChange={setProfile}
                  style={{ width: '100%', marginTop: 8 }}
                  options={(profileData?.profiles || []).map((p: any) => ({ value: p.id, label: p.name }))}
                />
              </Col>
              <Col xs={24} lg={8}>
                <Text strong>求解模式</Text>
                <Select
                  value={mode}
                  onChange={setMode}
                  style={{ width: '100%', marginTop: 8 }}
                  options={[
                    { value: 'current', label: '当前利润' },
                    { value: 'target_profit', label: '目标利润' },
                    { value: 'target_margin', label: '目标利润率' },
                    { value: 'target_roi', label: '目标ROI' },
                  ]}
                />
              </Col>
              <Col xs={24} lg={8}>
                <Alert type="info" showIcon message="参数来源优先级" description="平台自动值 → 店铺默认值 → SKU 覆盖值 → 本次模拟临时值" />
              </Col>
            </Row>

            <Tabs
              style={{ marginTop: 12 }}
              items={[
                {
                  key: 'platform',
                  label: '平台自动值',
                  children: <Space><InputNumber addonBefore="变量费率" value={layers.platform_auto.variable_rate_total} onChange={(v) => setLayers({ ...layers, platform_auto: { ...layers.platform_auto, variable_rate_total: Number(v || 0) } })} /><InputNumber addonBefore="固定成本" value={layers.platform_auto.fixed_cost_total} onChange={(v) => setLayers({ ...layers, platform_auto: { ...layers.platform_auto, fixed_cost_total: Number(v || 0) } })} /></Space>
                },
                {
                  key: 'shop',
                  label: '店铺默认值',
                  children: <Space><InputNumber addonBefore="变量费率" value={layers.shop_default.variable_rate_total} onChange={(v) => setLayers({ ...layers, shop_default: { ...layers.shop_default, variable_rate_total: Number(v || 0) } })} /><InputNumber addonBefore="固定成本" value={layers.shop_default.fixed_cost_total} onChange={(v) => setLayers({ ...layers, shop_default: { ...layers.shop_default, fixed_cost_total: Number(v || 0) } })} /></Space>
                },
                {
                  key: 'sku',
                  label: 'SKU 覆盖值',
                  children: <Space><InputNumber addonBefore="变量费率" value={layers.sku_override.variable_rate_total} onChange={(v) => setLayers({ ...layers, sku_override: { ...layers.sku_override, variable_rate_total: Number(v || 0) } })} /><InputNumber addonBefore="固定成本" value={layers.sku_override.fixed_cost_total} onChange={(v) => setLayers({ ...layers, sku_override: { ...layers.sku_override, fixed_cost_total: Number(v || 0) } })} /></Space>
                },
                {
                  key: 'sim',
                  label: '本次模拟临时值',
                  children: <Space><InputNumber addonBefore="变量费率" value={layers.simulation_override.variable_rate_total} onChange={(v) => setLayers({ ...layers, simulation_override: { ...layers.simulation_override, variable_rate_total: Number(v || 0) } })} /><InputNumber addonBefore="固定成本" value={layers.simulation_override.fixed_cost_total} onChange={(v) => setLayers({ ...layers, simulation_override: { ...layers.simulation_override, fixed_cost_total: Number(v || 0) } })} /></Space>
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Divider style={{ margin: '12px 0' }} />

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={10}>
          <Card size="small" title={<span><CalculatorOutlined /> 求解输入区</span>} bodyStyle={{ padding: 16 }}>
            <Form form={form} layout="vertical" initialValues={{ salePrice: 119, listPrice: 129, variableRateTotal: 0.31, fixedCostTotal: 72, targetValue: 0 }}>
              <Form.Item label="售价" name="salePrice" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={1} /></Form.Item>
              <Form.Item label="原价" name="listPrice" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={1} /></Form.Item>
              <Form.Item label="变量费率总和" name="variableRateTotal" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} max={1} step={0.01} /></Form.Item>
              <Form.Item label="固定成本总和" name="fixedCostTotal" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
              <Form.Item label="目标值(按模式)" name="targetValue"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
              <Button type="primary" icon={<PlayCircleOutlined />} loading={isFetching} onClick={onCalculate} block>运行算法求解</Button>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card size="small" title="多情景对比设置" bodyStyle={{ padding: 12 }}>
            <Table rowKey="key" pagination={false} dataSource={scenarios} columns={scenarioColumns} size="small" />
          </Card>
        </Col>
      </Row>

      <Divider style={{ margin: '12px 0' }} />

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={8}><Card size="small"><Statistic title="当前净利润" value={current?.net_profit || 0} precision={2} /></Card></Col>
        <Col xs={24} lg={8}><Card size="small"><Statistic title="当前净利率" value={(current?.net_margin || 0) * 100} precision={2} suffix="%" /></Card></Col>
        <Col xs={24} lg={8}><Card size="small"><Statistic title="建议售价" value={solveData?.suggested_price || 0} precision={2} /></Card></Col>
      </Row>

      <Divider />

      <Collapse
        defaultActiveKey={[]}
        items={[
          {
            key: 'advanced',
            label: '高级分析区（参数状态 / 风险扫描 / 快照模板 / 模拟结果）',
            children: (
              <>
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card title="参数来源状态（按变量）" extra={<Space><Button loading={saveSnapshotMutation.isPending} onClick={handleSaveSnapshot}>保存快照</Button><Button type="primary" loading={saveTemplateMutation.isPending} onClick={handleSaveTemplate}>保存模板</Button></Space>}>
                      <Table pagination={false} size="small" rowKey="variable" dataSource={sourceStatusRows} columns={[
                        { title: '变量', dataIndex: 'variable', key: 'variable' },
                        { title: '当前值', dataIndex: 'value', key: 'value' },
                        { title: '来源', dataIndex: 'source', key: 'source', render: (v: string) => <Tag color={v === 'simulation' ? 'purple' : v === 'sku' ? 'blue' : v === 'shop' ? 'cyan' : 'green'}>{v === 'simulation' ? '本次模拟值' : v === 'sku' ? 'SKU覆盖值' : v === 'shop' ? '店铺默认值' : '平台自动值'}</Tag> },
                      ]} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="利润构成拆分">
                      <Table pagination={false} size="small" rowKey="item" dataSource={profitBreakdown} columns={[
                        { title: '构成项', dataIndex: 'item', key: 'item' },
                        { title: '金额', dataIndex: 'value', key: 'value', render: (v: number) => `¥${Number(v || 0).toFixed(2)}` },
                      ]} />
                    </Card>
                  </Col>
                </Row>

                <Divider />

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card title="场景解读建议">
                      <List dataSource={scenarioInterpretation} renderItem={(x: any) => <List.Item><List.Item.Meta title={x.name} description={x.note} /></List.Item>} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="异常扫描 / 风险检测">
                      <Table pagination={false} size="small" rowKey="risk" dataSource={riskScan} columns={[
                        { title: '风险项', dataIndex: 'risk', key: 'risk' },
                        { title: '等级', dataIndex: 'level', key: 'level', render: (v: string) => <OpsRiskTag level={v === '高' ? 'critical' : v === '中' ? 'warning' : 'normal'} /> },
                        { title: '说明', dataIndex: 'detail', key: 'detail' },
                      ]} />
                    </Card>
                  </Col>
                </Row>

                <Divider />

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card title="已保存快照"><List size="small" dataSource={snapshotData?.snapshots || []} renderItem={(item: any) => <List.Item>{item.snapshotName} / {item.algorithmProfile} / {item.savedAt}</List.Item>} /></Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="已保存模板"><List size="small" dataSource={templateData?.templates || []} renderItem={(item: any) => <List.Item>{item.templateName} / {item.algorithmProfile} / {item.savedAt}</List.Item>} /></Card>
                  </Col>
                </Row>

                <Divider />

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card title="折扣模拟结果"><Table rowKey={(r: any) => `${r.discount_ratio}`} pagination={false} dataSource={solveData?.discounts || []} columns={[
                      { title: '折扣系数', dataIndex: 'discount_ratio', key: 'discount_ratio' },
                      { title: '成交价', dataIndex: 'deal_price', key: 'deal_price' },
                      { title: '净利润', dataIndex: 'net_profit', key: 'net_profit' },
                      { title: '净利率', dataIndex: 'net_margin', key: 'net_margin', render: (v: number) => `${(v * 100).toFixed(2)}%` },
                    ]} size="small" /></Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="多情景结果对比"><Table rowKey="name" pagination={false} dataSource={solveData?.scenario_results || []} columns={scenarioResultColumns} size="small" /></Card>
                  </Col>
                </Row>
              </>
            ),
          },
        ]}
      />
    </div>
  )
}
