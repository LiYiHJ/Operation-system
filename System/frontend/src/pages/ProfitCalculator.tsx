import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Divider,
  Form,
  InputNumber,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import { CalculatorOutlined, PlayCircleOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { integrationApi, profitApi, thematicApi } from '../services/api'
import { formatCurrency, formatPercent, formatRate } from '../utils/format'
import { OpsConclusion, OpsPageHeader, OpsRiskTag } from '../components/ops/ProductSection'

const { Text } = Typography

type LayeredParams = {
  platform_auto: Record<string, number>
  shop_default: Record<string, number>
  sku_override: Record<string, number>
  simulation_override: Record<string, number>
}

type SourceTag = 'platform_auto' | 'shop_default' | 'sku_override' | 'simulation_override'

type TransportOption = {
  key: string
  warehouse: string
  provider: string
  serviceLevel: 'Express' | 'Standard' | 'Economy'
  deliveryType: 'pickup' | 'door'
  productTier: string
  firstMile: number
  fulfillment: number
  storage: number
  lastMile: number
  handlingFee: number
  defaultWeight: number
  defaultVolume: number
}

const SOURCE_LABEL: Record<SourceTag, string> = {
  platform_auto: '平台自动值',
  shop_default: '店铺默认值',
  sku_override: 'SKU覆盖值',
  simulation_override: '本次模拟值',
}

const SOURCE_COLOR: Record<SourceTag, string> = {
  platform_auto: 'blue',
  shop_default: 'cyan',
  sku_override: 'gold',
  simulation_override: 'magenta',
}

const VARIABLE_ITEMS = [
  { key: 'platform_commission_rate', label: '平台佣金率' },
  { key: 'payment_rate', label: '支付费率' },
  { key: 'tax_rate', label: '税率' },
  { key: 'ads_rate', label: '广告费率' },
  { key: 'fx_loss_rate', label: '汇率损失率' },
  { key: 'after_sales_loss_rate', label: '退款/售后损耗率' },
  { key: 'other_variable_rate', label: '其他变动费率' },
]

const FIXED_ITEMS = [
  { key: 'purchase_cost', label: '采购成本' },
  { key: 'first_mile_cost', label: '头程成本' },
  { key: 'packaging_cost', label: '包装成本' },
  { key: 'fulfillment_cost', label: '履约成本' },
  { key: 'storage_cost', label: '仓储成本' },
  { key: 'last_mile_cost', label: '最后一公里成本' },
  { key: 'ads_allocation_cost', label: '广告分摊' },
  { key: 'return_loss_cost', label: '退货损失' },
  { key: 'cancel_loss_cost', label: '取消损失' },
  { key: 'promotion_subsidy_cost', label: '促销补贴' },
  { key: 'other_fixed_cost', label: '其他固定成本' },
]

const TRANSPORT_OPTIONS: TransportOption[] = [
  {
    key: 'yiwu-standard-small',
    warehouse: '义乌仓',
    provider: 'OZON Logistic',
    serviceLevel: 'Standard',
    deliveryType: 'pickup',
    productTier: 'Small',
    firstMile: 6.5,
    fulfillment: 4.2,
    storage: 1.2,
    lastMile: 7.1,
    handlingFee: 2.1,
    defaultWeight: 0.35,
    defaultVolume: 0.004,
  },
  {
    key: 'yiwu-express-budget',
    warehouse: '义乌仓',
    provider: '4PX',
    serviceLevel: 'Express',
    deliveryType: 'door',
    productTier: 'Budget',
    firstMile: 8.8,
    fulfillment: 5.3,
    storage: 1.6,
    lastMile: 9.6,
    handlingFee: 2.6,
    defaultWeight: 0.42,
    defaultVolume: 0.005,
  },
  {
    key: 'yiwu-economy-extra-small',
    warehouse: '义乌仓',
    provider: 'Cainiao',
    serviceLevel: 'Economy',
    deliveryType: 'pickup',
    productTier: 'Extra Small',
    firstMile: 4.9,
    fulfillment: 3.6,
    storage: 1.0,
    lastMile: 5.7,
    handlingFee: 1.8,
    defaultWeight: 0.2,
    defaultVolume: 0.0025,
  },
]

const buildDefaultLayered = (): LayeredParams => ({
  platform_auto: {
    platform_commission_rate: 0.16,
    payment_rate: 0.02,
    tax_rate: 0.06,
    ads_rate: 0.07,
    fx_loss_rate: 0.01,
    after_sales_loss_rate: 0.01,
    other_variable_rate: 0.01,
    purchase_cost: 45,
    first_mile_cost: 6,
    packaging_cost: 2.8,
    fulfillment_cost: 4,
    storage_cost: 1.5,
    last_mile_cost: 6.8,
    ads_allocation_cost: 3.2,
    return_loss_cost: 1.2,
    cancel_loss_cost: 0.8,
    promotion_subsidy_cost: 2,
    other_fixed_cost: 1.5,
    sale_price: 119,
    list_price: 139,
    shop_campaign_price: 112,
    platform_campaign_price: 105,
    coupon_final_price: 101,
    refund_rate_hint: 0.02,
    recent_margin_hint: 0.11,
  },
  shop_default: {
    ads_rate: 0.05,
    fx_loss_rate: 0.008,
    purchase_cost: 42,
    first_mile_cost: 5.5,
    fulfillment_cost: 3.8,
    storage_cost: 1.2,
    list_price: 136,
  },
  sku_override: {},
  simulation_override: {},
})

function resolveLayerValue(layers: LayeredParams, key: string): { value: number; source: SourceTag } {
  if (layers.simulation_override[key] != null) return { value: Number(layers.simulation_override[key]), source: 'simulation_override' }
  if (layers.sku_override[key] != null) return { value: Number(layers.sku_override[key]), source: 'sku_override' }
  if (layers.shop_default[key] != null) return { value: Number(layers.shop_default[key]), source: 'shop_default' }
  return { value: Number(layers.platform_auto[key] || 0), source: 'platform_auto' }
}

function calcTransportCosts(option: TransportOption, weight: number, volume: number, isSensitive: boolean, cargoValue: number) {
  const weightFactor = Math.max(weight / option.defaultWeight, 0.6)
  const volumeFactor = Math.max(volume / option.defaultVolume, 0.6)
  const sensitiveFactor = isSensitive ? 1.15 : 1
  const cargoFactor = cargoValue > 120 ? 1.08 : 1

  const firstMile = Number((option.firstMile * weightFactor * sensitiveFactor).toFixed(2))
  const fulfillment = Number((option.fulfillment * volumeFactor).toFixed(2))
  const storage = Number((option.storage * volumeFactor).toFixed(2))
  const lastMile = Number((option.lastMile * weightFactor * cargoFactor).toFixed(2))
  const handlingFee = Number((option.handlingFee * sensitiveFactor).toFixed(2))

  return {
    firstMile,
    fulfillment,
    storage,
    lastMile,
    handlingFee,
    total: Number((firstMile + fulfillment + storage + lastMile + handlingFee).toFixed(2)),
  }
}

export default function ProfitCalculator() {
  const [form] = Form.useForm()
  const [topView, setTopView] = useState<'decision' | 'rules'>('decision')
  const [scenarioMode, setScenarioMode] = useState<'pre_listing' | 'post_listing'>('post_listing')
  const [profile, setProfile] = useState('ozon_daily_profit')
  const [mode, setMode] = useState('current')
  const [layers, setLayers] = useState<LayeredParams>(buildDefaultLayered)
  const [discountPoints, setDiscountPoints] = useState<number[]>([0.95, 0.9, 0.85, 0.8])
  const [customDiscount, setCustomDiscount] = useState<number | null>(null)
  const [transportKey, setTransportKey] = useState<string>(TRANSPORT_OPTIONS[0].key)
  const [transportWeight, setTransportWeight] = useState<number>(TRANSPORT_OPTIONS[0].defaultWeight)
  const [transportVolume, setTransportVolume] = useState<number>(TRANSPORT_OPTIONS[0].defaultVolume)
  const [transportSensitive, setTransportSensitive] = useState<number>(0)
  const [cargoValue, setCargoValue] = useState<number>(110)
  const [scenarios, setScenarios] = useState<any[]>([
    { key: 'base', name: '日常价', sale_price: 119, list_price: 139 },
    { key: 'platform_campaign', name: '平台活动价', sale_price: 105, list_price: 139 },
    { key: 'self_promo', name: '自建促销价', sale_price: 99, list_price: 139 },
    { key: 'margin_floor', name: '保利润底线价', sale_price: 113, list_price: 139 },
    { key: 'volume_test', name: '冲量测试价', sale_price: 95, list_price: 139 },
  ])

  const [requestPayload, setRequestPayload] = useState<any>(() => ({
    mode: 'current',
    targetValue: 0,
    salePrice: 119,
    listPrice: 139,
    variableRateTotal: 0.34,
    fixedCostTotal: 74,
    algorithmProfile: 'ozon_daily_profit',
    layeredParams: buildDefaultLayered(),
    scenarios: scenarios.map((s) => ({ name: s.name, layered_params: { simulation_override: { sale_price: s.sale_price, list_price: s.list_price } } })),
  }))

  const { data: profileData } = useQuery({ queryKey: ['profit-profiles'], queryFn: () => profitApi.getProfiles(), staleTime: 300_000 })
  const { data: solveData, isFetching } = useQuery({ queryKey: ['profit-solve', requestPayload], queryFn: () => profitApi.solve(requestPayload), enabled: !!requestPayload })
  const { data: snapshotData, refetch: refetchSnapshots } = useQuery({ queryKey: ['profit-snapshots'], queryFn: () => profitApi.getSnapshots({ shopId: 1, limit: 10 }) })
  const { data: templateData, refetch: refetchTemplates } = useQuery({ queryKey: ['profit-templates'], queryFn: () => profitApi.getTemplates({ shopId: 1, limit: 10 }) })

  const { data: pricingAutofill } = useQuery({ queryKey: ['pricing-autofill'], queryFn: () => integrationApi.getPricingAutofill({ provider: 'ozon', shopId: 1 }), staleTime: 120000 })

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
      message.success('参数模板已保存为 SKU 覆盖')
      refetchTemplates()
    },
    onError: (error: any) => message.error(`保存模板失败: ${error.message}`),
  })

  const pushSalesMutation = useMutation({
    mutationFn: (payload: any) => integrationApi.pushSales(payload),
    onSuccess: () => message.success('已推送销售后台并写入推送日志'),
    onError: (error: any) => message.error(`推送失败: ${error.message}`),
  })

  const strategyMutation = useMutation({
    mutationFn: (payload: any) => thematicApi.pushActionToStrategy(payload),
    onSuccess: () => message.success('已生成策略动作，可在策略清单继续执行'),
    onError: (error: any) => message.error(`生成策略失败: ${error.message}`),
  })

  const variableRows = useMemo(
    () => VARIABLE_ITEMS.map((item) => ({ ...item, ...resolveLayerValue(layers, item.key) })),
    [layers],
  )
  const fixedRows = useMemo(
    () => FIXED_ITEMS.map((item) => ({ ...item, ...resolveLayerValue(layers, item.key) })),
    [layers],
  )

  const variableRateTotal = useMemo(() => Number(variableRows.reduce((sum, x) => sum + Number(x.value || 0), 0).toFixed(4)), [variableRows])
  const fixedCostTotal = useMemo(() => Number(fixedRows.reduce((sum, x) => sum + Number(x.value || 0), 0).toFixed(2)), [fixedRows])

  const salePriceResolved = resolveLayerValue(layers, 'sale_price')
  const listPriceResolved = resolveLayerValue(layers, 'list_price')
  const shopCampaignPrice = resolveLayerValue(layers, 'shop_campaign_price')
  const platformCampaignPrice = resolveLayerValue(layers, 'platform_campaign_price')
  const couponFinalPrice = resolveLayerValue(layers, 'coupon_final_price')

  useEffect(() => {
    form.setFieldsValue({ salePrice: salePriceResolved.value, listPrice: listPriceResolved.value, targetValue: 0 })
  }, [form, salePriceResolved.value, listPriceResolved.value])

  useEffect(() => {
    if (!pricingAutofill) return
    setLayers((prev) => ({
      ...prev,
      platform_auto: { ...prev.platform_auto, ...pricingAutofill },
    }))
  }, [pricingAutofill])

  const updateSimulationValue = (key: string, value: number) => {
    setLayers((prev) => ({ ...prev, simulation_override: { ...prev.simulation_override, [key]: value } }))
  }

  const saveAsSkuOverride = (key: string) => {
    const value = layers.simulation_override[key]
    if (value == null) return
    setLayers((prev) => {
      const simulationOverride = { ...prev.simulation_override }
      delete simulationOverride[key]
      return { ...prev, simulation_override: simulationOverride, sku_override: { ...prev.sku_override, [key]: value } }
    })
  }

  const restoreFromParent = (key: string) => {
    setLayers((prev) => {
      const next = { ...prev, simulation_override: { ...prev.simulation_override } }
      delete next.simulation_override[key]
      return next
    })
  }

  const applyTransport = () => {
    const option = TRANSPORT_OPTIONS.find((x) => x.key === transportKey)
    if (!option) return
    const costs = calcTransportCosts(option, transportWeight, transportVolume, !!transportSensitive, cargoValue)
    updateSimulationValue('first_mile_cost', costs.firstMile)
    updateSimulationValue('fulfillment_cost', costs.fulfillment)
    updateSimulationValue('storage_cost', costs.storage)
    updateSimulationValue('last_mile_cost', costs.lastMile)
    updateSimulationValue('other_fixed_cost', Number((resolveLayerValue(layers, 'other_fixed_cost').value + costs.handlingFee).toFixed(2)))
    message.success(`运输方案已回填，运输相关固定成本合计 ${formatCurrency(costs.total)}`)
  }

  const onCalculate = async () => {
    const values = await form.validateFields()
    const payload = {
      mode,
      targetValue: values.targetValue || 0,
      salePrice: values.salePrice,
      listPrice: values.listPrice,
      variableRateTotal,
      fixedCostTotal,
      algorithmProfile: profile,
      layeredParams: layers,
      scenarios: scenarios.map((s) => ({
        name: s.name,
        layered_params: { simulation_override: { sale_price: s.sale_price, list_price: s.list_price } },
      })),
    }
    setRequestPayload(payload)
  }

  const addDiscountPoint = () => {
    if (!customDiscount || customDiscount <= 0 || customDiscount >= 1) return
    const rounded = Number(customDiscount.toFixed(2))
    if (discountPoints.includes(rounded)) return
    setDiscountPoints((prev) => [...prev, rounded].sort((a, b) => b - a))
    setCustomDiscount(null)
  }

  const applySuggestionPrice = () => {
    const suggested = Number(solveData?.suggested_price || 0)
    if (!suggested) return
    updateSimulationValue('sale_price', suggested)
    form.setFieldValue('salePrice', suggested)
    message.success('已套用建议售价')
  }

  const restoreCurrentPrice = () => {
    restoreFromParent('sale_price')
    form.setFieldValue('salePrice', resolveLayerValue(layers, 'sale_price').value)
    message.success('已恢复上级来源售价')
  }

  const toggleScenarioMode = (next: 'pre_listing' | 'post_listing') => {
    setScenarioMode(next)
    if (next === 'pre_listing') {
      setLayers((prev) => ({
        ...prev,
        simulation_override: {
          ...prev.simulation_override,
          ads_rate: 0.04,
          return_loss_cost: 0.8,
          cancel_loss_cost: 0.6,
        },
      }))
      message.info('已切换到上品前定价：采用模板估算值')
      return
    }
    setLayers((prev) => ({
      ...prev,
      simulation_override: {
        ...prev.simulation_override,
        ads_rate: 0.065,
        return_loss_cost: 1.5,
        cancel_loss_cost: 1.1,
      },
    }))
    message.info('已切换到上品后调价：回填近期运营均值')
  }

  const current = solveData?.current
  const riskScan = solveData?.riskScan || []

  const scenarioColumns = [
    { title: '场景', dataIndex: 'name', width: 140 },
    {
      title: '成交价',
      dataIndex: 'sale_price',
      width: 110,
      render: (v: number, _r: any, idx: number) => <InputNumber value={v} min={1} onChange={(val) => setScenarios((prev) => prev.map((s, i) => i === idx ? { ...s, sale_price: Number(val || 0) } : s))} />,
    },
    {
      title: '原价',
      dataIndex: 'list_price',
      width: 110,
      render: (v: number, _r: any, idx: number) => <InputNumber value={v} min={1} onChange={(val) => setScenarios((prev) => prev.map((s, i) => i === idx ? { ...s, list_price: Number(val || 0) } : s))} />,
    },
  ]

  const scenarioResultColumns = [
    { title: '场景', dataIndex: 'name', width: 140, ellipsis: true },
    { title: '成交价', dataIndex: ['result', 'sale_price'], width: 96, render: (_: any, row: any) => formatCurrency(row?.sale_price || row?.result?.sale_price || 0) },
    { title: '净利润', dataIndex: ['result', 'net_profit'], width: 100, render: (v: number) => formatCurrency(v) },
    { title: '净利率', dataIndex: ['result', 'net_margin'], width: 95, render: (v: number) => formatPercent(v, 2, true) },
    { title: '盈亏', dataIndex: ['result', 'is_loss'], width: 80, render: (v: boolean) => <Tag color={v ? 'red' : 'green'}>{v ? '亏损' : '盈利'}</Tag> },
    {
      title: '相对当前差值',
      width: 130,
      render: (_: any, row: any) => {
        const delta = Number(row?.result?.net_profit || 0) - Number(current?.net_profit || 0)
        return <Text type={delta < 0 ? 'danger' : 'success'}>{delta >= 0 ? '+' : ''}{formatCurrency(delta)}</Text>
      },
    },
  ]

  const breakEvenDiscount = listPriceResolved.value > 0
    ? Number((1 - (Number(current?.break_even_price || 0) / listPriceResolved.value)).toFixed(4))
    : 0

  const discountRows = useMemo(() => {
    const saleBase = Number(salePriceResolved.value || 0)
    return discountPoints.map((ratio) => {
      const predictedSale = Number((saleBase * ratio).toFixed(2))
      const netProfit = Number((predictedSale * (1 - variableRateTotal) - fixedCostTotal).toFixed(2))
      const netMargin = predictedSale > 0 ? Number((netProfit / predictedSale).toFixed(4)) : 0
      const loss = netProfit < 0
      const belowBreakEven = breakEvenDiscount > 0 && ratio < 1 - breakEvenDiscount
      return { ratio, predictedSale, netProfit, netMargin, loss, belowBreakEven }
    })
  }, [discountPoints, salePriceResolved.value, variableRateTotal, fixedCostTotal, breakEvenDiscount])

  const selectedTransport = TRANSPORT_OPTIONS.find((x) => x.key === transportKey) || TRANSPORT_OPTIONS[0]
  const transportPreview = calcTransportCosts(selectedTransport, transportWeight, transportVolume, !!transportSensitive, cargoValue)

  const variableColumns = [
    { title: '费率项', dataIndex: 'label', width: 170, ellipsis: true },
    {
      title: '当前值',
      dataIndex: 'value',
      width: 150,
      render: (v: number, row: any) => (
        <InputNumber value={v} min={0} max={1} step={0.005} onChange={(val) => updateSimulationValue(row.key, Number(val || 0))} style={{ width: '100%' }} />
      ),
    },
    { title: '来源', dataIndex: 'source', width: 120, render: (v: SourceTag) => <Tag color={SOURCE_COLOR[v]}>{SOURCE_LABEL[v]}</Tag> },
    {
      title: '操作',
      width: 130,
      render: (_: any, row: any) => (
        <Space size={4}>
          <Button size="small" icon={<ReloadOutlined />} disabled={row.source !== 'simulation_override'} onClick={() => restoreFromParent(row.key)} />
          <Button size="small" onClick={() => saveAsSkuOverride(row.key)} disabled={row.source !== 'simulation_override'}>存SKU</Button>
        </Space>
      ),
    },
  ]

  const fixedColumns = [
    { title: '成本项', dataIndex: 'label', width: 170, ellipsis: true },
    {
      title: '当前值',
      dataIndex: 'value',
      width: 150,
      render: (v: number, row: any) => <InputNumber value={v} min={0} step={0.1} onChange={(val) => updateSimulationValue(row.key, Number(val || 0))} style={{ width: '100%' }} />,
    },
    { title: '来源', dataIndex: 'source', width: 120, render: (v: SourceTag) => <Tag color={SOURCE_COLOR[v]}>{SOURCE_LABEL[v]}</Tag> },
    {
      title: '操作',
      width: 130,
      render: (_: any, row: any) => (
        <Space size={4}>
          <Button size="small" icon={<ReloadOutlined />} disabled={row.source !== 'simulation_override'} onClick={() => restoreFromParent(row.key)} />
          <Button size="small" onClick={() => saveAsSkuOverride(row.key)} disabled={row.source !== 'simulation_override'}>存SKU</Button>
        </Space>
      ),
    },
  ]

  const decisionView = (
    <Space direction="vertical" style={{ width: '100%' }} size={12}>
      <Card size="small" title="平台价格结构（展示价 vs 求解价）">
        <Row gutter={[12, 12]}>
          <Col xs={24} lg={4}><Statistic title="划线原价 list_price" value={listPriceResolved.value} precision={2} /></Col>
          <Col xs={24} lg={4}><Statistic title="店铺活动价" value={shopCampaignPrice.value} precision={2} /></Col>
          <Col xs={24} lg={4}><Statistic title="平台活动价" value={platformCampaignPrice.value} precision={2} /></Col>
          <Col xs={24} lg={4}><Statistic title="券后预计成交价" value={couponFinalPrice.value} precision={2} /></Col>
          <Col xs={24} lg={8}>
            <Alert
              type="info"
              showIcon
              message={`本次求解使用成交价 sale_price = ${formatCurrency(salePriceResolved.value)}`}
              description="利润公式实际使用最终成交价 sale_price，而非划线原价 list_price。"
            />
          </Col>
        </Row>
      </Card>

      <OpsConclusion
        title="定价决策结论"
        desc={`当前净利润 ${formatCurrency(current?.net_profit || 0)}，净利率 ${formatPercent(current?.net_margin || 0, 2, true)}，建议售价 ${formatCurrency(solveData?.suggested_price || 0)}。`}
        level={(current?.is_loss || (current?.net_margin || 0) < 0.08) ? 'warning' : 'success'}
      />

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={5}><Card size="small"><Statistic title="当前净利润" value={current?.net_profit || 0} precision={2} /></Card></Col>
        <Col xs={24} lg={5}><Card size="small"><Statistic title="当前净利率" value={(current?.net_margin || 0) * 100} precision={2} suffix="%" /></Card></Col>
        <Col xs={24} lg={5}><Card size="small"><Statistic title="建议售价" value={solveData?.suggested_price || 0} precision={2} /></Card></Col>
        <Col xs={24} lg={5}><Card size="small"><Statistic title="保本价" value={current?.break_even_price || 0} precision={2} /></Card></Col>
        <Col xs={24} lg={4}><Card size="small"><Statistic title="保本折扣率" value={breakEvenDiscount * 100} precision={2} suffix="%" /></Card></Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={10}>
          <Card size="small" title={<span><CalculatorOutlined /> 主决策输入区</span>}>
            <Form form={form} layout="vertical" initialValues={{ salePrice: salePriceResolved.value, listPrice: listPriceResolved.value, targetValue: 0 }}>
              <Form.Item label="求解模式">
                <Select value={mode} onChange={setMode} options={[{ value: 'current', label: '当前利润' }, { value: 'target_profit', label: '目标利润' }, { value: 'target_margin', label: '目标净利率' }, { value: 'target_roi', label: '目标ROI' }]} />
              </Form.Item>
              <Form.Item label="目标值" name="targetValue">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
              <Form.Item label={<Space>当前成交价 <Tag color={SOURCE_COLOR[salePriceResolved.source]}>{SOURCE_LABEL[salePriceResolved.source]}</Tag></Space>} name="salePrice" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={1} onChange={(v) => updateSimulationValue('sale_price', Number(v || 0))} />
              </Form.Item>
              <Form.Item label={<Space>原价 <Tag color={SOURCE_COLOR[listPriceResolved.source]}>{SOURCE_LABEL[listPriceResolved.source]}</Tag></Space>} name="listPrice" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} min={1} onChange={(v) => updateSimulationValue('list_price', Number(v || 0))} />
              </Form.Item>
              <Form.Item label="variable_rate_total（自动汇总）"><InputNumber value={variableRateTotal} disabled style={{ width: '100%' }} /></Form.Item>
              <Form.Item label="fixed_cost_total（自动汇总）"><InputNumber value={fixedCostTotal} disabled style={{ width: '100%' }} /></Form.Item>
              <Space style={{ width: '100%' }}>
                <Button type="primary" icon={<PlayCircleOutlined />} loading={isFetching} onClick={onCalculate}>运行算法求解</Button>
                <Button onClick={applySuggestionPrice}>一键套用建议售价</Button>
                <Button onClick={restoreCurrentPrice}>一键恢复当前售价</Button>
              </Space>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card size="small" title="多情景结果对比（前置）" extra={<Tag color="purple">核心调价对比区</Tag>}>
            <Table rowKey="key" pagination={false} dataSource={scenarios} columns={scenarioColumns as any} size="small" scroll={{ x: 520, y: 180 }} tableLayout="fixed" />
            <Divider style={{ margin: '10px 0' }} />
            <Table rowKey="name" pagination={false} dataSource={solveData?.scenario_results || []} columns={scenarioResultColumns as any} size="small" scroll={{ x: 860, y: 220 }} tableLayout="fixed" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={14}>
          <Card size="small" title="折扣模拟结果（前置）" extra={<Tag color="orange">低于保本折扣自动预警</Tag>}>
            <Space style={{ marginBottom: 10 }}>
              {discountPoints.map((p) => <Tag key={p}>{(p * 100).toFixed(0)}折</Tag>)}
              <InputNumber min={0.5} max={0.99} step={0.01} value={customDiscount as any} onChange={(v) => setCustomDiscount(v as number)} placeholder="手工折扣点" />
              <Button onClick={addDiscountPoint}>增加折扣点</Button>
            </Space>
            <Table
              rowKey={(r: any) => String(r.ratio)}
              pagination={false}
              size="small"
              scroll={{ x: 760, y: 220 }}
              tableLayout="fixed"
              dataSource={discountRows}
              columns={[
                { title: '折扣系数', dataIndex: 'ratio', width: 90, render: (v: number) => v.toFixed(2) },
                { title: '成交价', dataIndex: 'predictedSale', width: 110, render: (v: number) => formatCurrency(v) },
                { title: '净利润', dataIndex: 'netProfit', width: 110, render: (v: number) => formatCurrency(v) },
                { title: '净利率', dataIndex: 'netMargin', width: 110, render: (v: number) => formatPercent(v, 2, true) },
                { title: '是否亏损', dataIndex: 'loss', width: 90, render: (v: boolean) => <Tag color={v ? 'red' : 'green'}>{v ? '亏损' : '盈利'}</Tag> },
                {
                  title: '保本检测',
                  dataIndex: 'belowBreakEven',
                  width: 140,
                  render: (v: boolean) => v ? <Tag color="red">低于保本折扣率</Tag> : <Tag color="blue">安全区</Tag>,
                },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card size="small" title="调价敏感度分析" extra={<Tag color="geekblue">基于当前公式推导</Tag>}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert type="info" showIcon message={`售价每 +1 元，净利润约 ${formatCurrency(1 - variableRateTotal)}`} />
              <Alert type="warning" showIcon message={`广告费率每 +1pct，净利润约 ${formatCurrency(-salePriceResolved.value * 0.01)}`} />
              <Alert type="error" showIcon message="固定成本每 +1 元，净利润约 -¥1.00" />
              <Card size="small" bordered={false} style={{ background: '#fafafa' }}>
                <Text type="secondary">建议：若利润被折扣压缩，优先看售价；若投放波动大，先收敛广告费率；若运输成本波动，优先切换运输方案。</Text>
              </Card>
            </Space>
          </Card>

          <Card size="small" title="动作闭环" style={{ marginTop: 12 }}>
            <Space wrap>
              <Button loading={saveSnapshotMutation.isPending} onClick={() => saveSnapshotMutation.mutate({ shopId: 1, snapshotName: `profit_snapshot_${Date.now()}`, algorithmProfile: profile, payload: requestPayload, result: solveData })}>保存快照</Button>
              <Button loading={saveTemplateMutation.isPending} onClick={() => saveTemplateMutation.mutate({ shopId: 1, templateName: `sku_override_${Date.now()}`, algorithmProfile: profile, layeredParams: layers, scenarios, operator: 'operator' })}>保存为SKU覆盖参数</Button>
              <Button onClick={() => setScenarios((prev) => prev.map((x) => x.key === 'platform_campaign' ? { ...x, sale_price: Number((salePriceResolved.value * 0.88).toFixed(2)) } : x))}>生成活动价方案</Button>
              <Button icon={<SendOutlined />} loading={pushSalesMutation.isPending} onClick={() => pushSalesMutation.mutate({ shopId: 1, payload: { sku: 'SKU-PROFIT-001', actionType: 'pricing', actionBefore: `sale_price=${salePriceResolved.value}`, actionAfter: `sale_price=${solveData?.suggested_price || salePriceResolved.value}`, sourcePage: 'profit', sourceReason: 'profit_calculator', operator: 'operator', confirmedAt: new Date().toISOString() } })}>推送销售后台</Button>
              <Button type="primary" loading={strategyMutation.isPending} onClick={() => strategyMutation.mutate({ shopId: 1, sourcePage: 'profit', sku: 'SKU-PROFIT-001', issueSummary: `当前净利率 ${formatPercent(current?.net_margin || 0, 2, true)}`, recommendedAction: `建议售价调整到 ${formatCurrency(solveData?.suggested_price || salePriceResolved.value)}`, strategyType: 'pricing', priority: (current?.is_loss || (current?.net_margin || 0) < 0.08) ? 'P0' : 'P1', operator: 'operator' })}>写入执行记录/策略</Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  )

  const rulesView = (
    <Collapse
      defaultActiveKey={['scene', 'transport', 'source', 'risk']}
      items={[
        {
          key: 'scene',
          label: '上品前 / 上品后 场景模式',
          children: (
            <Card size="small" bordered={false}>
              <Row gutter={[12, 12]} align="middle">
                <Col xs={24} lg={9}>
                  <Segmented
                    block
                    value={scenarioMode}
                    onChange={(v) => toggleScenarioMode(v as any)}
                    options={[{ label: '上品前定价（模板估算）', value: 'pre_listing' }, { label: '上品后调价（真实数据回填）', value: 'post_listing' }]}
                  />
                </Col>
                <Col xs={24} lg={15}>
                  {scenarioMode === 'pre_listing'
                    ? <Alert type="info" showIcon message="当前模式：模板估算" description="使用类目/店铺默认模板与运输方案估算，无历史真实成交数据。" />
                    : <Alert type="success" showIcon message="当前模式：真实数据回填" description="使用最近 7/15/30 天均值回填（广告费率、物流、退款率等），并允许临时覆盖。" />}
                </Col>
              </Row>
            </Card>
          ),
        },
        {
          key: 'transport',
          label: '运输成本引擎（方案驱动回填）',
          children: (
            <Card size="small" title="运输方案选择" extra={<Tag color="blue">回填头程/履约/仓储/末端成本</Tag>}>
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={8}><Select value={transportKey} onChange={setTransportKey} style={{ width: '100%' }} options={TRANSPORT_OPTIONS.map((x) => ({ value: x.key, label: `${x.warehouse} / ${x.provider} / ${x.serviceLevel} / ${x.productTier}` }))} /></Col>
                <Col xs={24} lg={4}><InputNumber style={{ width: '100%' }} value={transportWeight} onChange={(v) => setTransportWeight(Number(v || 0))} addonAfter="kg" /></Col>
                <Col xs={24} lg={4}><InputNumber style={{ width: '100%' }} value={transportVolume} onChange={(v) => setTransportVolume(Number(v || 0))} addonAfter="m³" /></Col>
                <Col xs={24} lg={4}><InputNumber style={{ width: '100%' }} value={cargoValue} onChange={(v) => setCargoValue(Number(v || 0))} addonAfter="货值" /></Col>
                <Col xs={24} lg={4}><Select style={{ width: '100%' }} value={transportSensitive} onChange={setTransportSensitive} options={[{ value: 0, label: '普通货' }, { value: 1, label: '带电/敏感货' }]} /></Col>
              </Row>
              <Divider style={{ margin: '12px 0' }} />
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={4}><Statistic title="头程" value={transportPreview.firstMile} precision={2} /></Col>
                <Col xs={24} lg={4}><Statistic title="履约" value={transportPreview.fulfillment} precision={2} /></Col>
                <Col xs={24} lg={4}><Statistic title="仓储" value={transportPreview.storage} precision={2} /></Col>
                <Col xs={24} lg={4}><Statistic title="末端" value={transportPreview.lastMile} precision={2} /></Col>
                <Col xs={24} lg={4}><Statistic title="操作费" value={transportPreview.handlingFee} precision={2} /></Col>
                <Col xs={24} lg={4}><Statistic title="运输相关合计" value={transportPreview.total} precision={2} /></Col>
              </Row>
              <Divider style={{ margin: '12px 0' }} />
              <Space>
                <Tag>{selectedTransport.deliveryType === 'pickup' ? '到取货点' : '到门'}</Tag>
                <Tag>{selectedTransport.serviceLevel}</Tag>
                <Tag>{selectedTransport.productTier}</Tag>
                <Button type="primary" onClick={applyTransport}>应用并回填到固定成本</Button>
              </Space>
            </Card>
          ),
        },
        {
          key: 'source',
          label: '变量费率 + 固定成本（明细可编辑 + 自动汇总 + 来源标签）',
          children: (
            <Row gutter={[12, 12]}>
              <Col xs={24} lg={12}>
                <Card size="small" title="变量费率明细">
                  <Table rowKey="key" dataSource={variableRows as any} columns={variableColumns as any} size="small" pagination={false} scroll={{ x: 560, y: 290 }} tableLayout="fixed" />
                  <Divider style={{ margin: '10px 0' }} />
                  <Text strong>variable_rate_total：{formatRate(variableRateTotal, 4)}</Text>
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card size="small" title="固定成本明细">
                  <Table rowKey="key" dataSource={fixedRows as any} columns={fixedColumns as any} size="small" pagination={false} scroll={{ x: 560, y: 290 }} tableLayout="fixed" />
                  <Divider style={{ margin: '10px 0' }} />
                  <Text strong>fixed_cost_total：{formatCurrency(fixedCostTotal)}</Text>
                </Card>
              </Col>
              <Col span={24}>
                <Alert type="info" showIcon message="参数来源优先级" description="平台自动值 → 店铺默认值 → SKU覆盖值 → 本次模拟值。关键字段支持一键恢复与保存 SKU 覆盖。" />
              </Col>
            </Row>
          ),
        },
        {
          key: 'risk',
          label: '风险扫描与建议',
          children: (
            <Card size="small">
              <Table
                size="small"
                rowKey={(x: any, i: number) => `${x?.name || x?.risk || 'risk'}-${i}`}
                dataSource={riskScan}
                pagination={false}
                scroll={{ x: 820, y: 260 }}
                tableLayout="fixed"
                columns={[
                  { title: '风险项', dataIndex: 'name', width: 150, ellipsis: true, render: (_: any, r: any) => r.name || r.risk || '风险项' },
                  { title: '级别', dataIndex: 'level', width: 90, render: (v: string) => <OpsRiskTag level={v === 'high' ? 'critical' : v === 'medium' ? 'warning' : 'normal'} /> },
                  { title: '说明', dataIndex: 'message', ellipsis: true, render: (v: string) => <Tooltip title={v}>{v || '—'}</Tooltip> },
                ]}
              />
            </Card>
          ),
        },
      ]}
    />
  )

  return (
    <div style={{ padding: 20 }}>
      <OpsPageHeader title="🧮 利润定价工作台" subtitle="面向上品前定价、上品后调价、活动前试算的真实运营场景。" />
      <Row gutter={[12, 12]} style={{ marginBottom: 10 }}>
        <Col xs={24} lg={10}>
          <Segmented
            block
            options={[{ label: '定价决策', value: 'decision' }, { label: '成本与规则', value: 'rules' }]}
            value={topView}
            onChange={(v) => setTopView(v as any)}
          />
        </Col>
        <Col xs={24} lg={8}>
          <Select value={profile} onChange={setProfile} style={{ width: '100%' }} options={(profileData?.profiles || []).map((p: any) => ({ value: p.id, label: p.name }))} />
        </Col>
        <Col xs={24} lg={6}>
          <Card size="small" bodyStyle={{ padding: 10 }}>
            <Space direction="vertical" size={0}>
              <Text type="secondary">当前风险</Text>
              <OpsRiskTag level={(current?.is_loss || (current?.net_margin || 0) < 0.08) ? 'warning' : 'normal'} />
            </Space>
          </Card>
        </Col>
      </Row>
      {topView === 'decision' ? decisionView : rulesView}
    </div>
  )
}
