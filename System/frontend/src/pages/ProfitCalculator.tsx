import React, { useState } from 'react'
import {
  Card,
  Row,
  Col,
  InputNumber,
  Input,
  Select,
  Button,
  Table,
  Tag,
  Alert,
  Divider,
  Space,
  Statistic,
  Progress,
  Tooltip,
  message,
  Form,
  Collapse,
  Typography
} from 'antd'
import {
  CalculatorOutlined,
  DollarOutlined,
  PercentageOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SettingOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse

// ===== 利润求解器页面 =====

interface ProfitInput {
  mode: 'current' | 'target_profit' | 'target_margin' | 'target_roi'
  sale_price?: number
  list_price: number
  variable_rate_total: number
  fixed_cost_total: number
  target_value?: number
}

interface ProfitResult {
  net_profit: number
  net_margin: number
  is_loss: boolean
  break_even_price: number
  break_even_discount_ratio?: number
  required_price?: number
  is_feasible?: boolean
}

interface CostBreakdown {
  // 变量费率
  platform_commission_rate: number
  payment_fee_rate: number
  tax_rate: number
  ad_rate: number
  exchange_loss_rate: number
  
  // 固定成本
  purchase_cost: number
  logistics_cost: number
  packaging_cost: number
  fulfillment_cost: number
  storage_cost: number
  last_mile_cost: number
  ad_allocation: number
  return_loss: number
  cancel_loss: number
  promotion_subsidy: number
  other_cost: number
}

export default function ProfitCalculator() {
  const [form] = Form.useForm()
  const [calculationMode, setCalculationMode] = useState<string>('current')
  const [profitInput, setProfitInput] = useState<ProfitInput | null>(null)
  const [costBreakdown, setCostBreakdown] = useState<CostBreakdown>({
    // 变量费率（默认值）
    platform_commission_rate: 0.15,
    payment_fee_rate: 0.02,
    tax_rate: 0.05,
    ad_rate: 0.10,
    exchange_loss_rate: 0.02,
    
    // 固定成本（默认值）
    purchase_cost: 50,
    logistics_cost: 20,
    packaging_cost: 3,
    fulfillment_cost: 10,
    storage_cost: 2,
    last_mile_cost: 15,
    ad_allocation: 10,
    return_loss: 5,
    cancel_loss: 2,
    promotion_subsidy: 5,
    other_cost: 2
  })
  
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // 计算利润
  const { data: profitResult, isLoading, refetch } = useQuery<ProfitResult | null>({
  queryKey: ['profit-calculation', profitInput],
  queryFn: async (): Promise<ProfitResult | null> => {
    if (!profitInput) return null
    
    // TODO: 调用后端 API
    // const { analysisApi } = await import('../services/api')
    // const response = await analysisApi.calculateProfit({
    //   salePrice: profitInput.sale_price || 0,
    //   listPrice: profitInput.list_price,
    //   variableRateTotal: profitInput.variable_rate_total,
    //   fixedCostTotal: profitInput.fixed_cost_total
    // })
    // return response.data
    
    // 模拟计算（前端演示）
    return calculateProfit(profitInput)
  },
  enabled: !!profitInput
})
  
  // 前端计算逻辑（演示用）
  const calculateProfit = (input: ProfitInput): ProfitResult => {
    const v = input.variable_rate_total
    const f = input.fixed_cost_total
    
    switch (input.mode) {
      case 'current': {
        const p = input.sale_price || 0
        const net_profit = p * (1 - v) - f
        const net_margin = p > 0 ? net_profit / p : 0
        const break_even_price = v < 1 ? f / (1 - v) : Infinity
        
        return {
          net_profit: Math.round(net_profit * 100) / 100,
          net_margin: Math.round(net_margin * 10000) / 10000,
          is_loss: net_profit < 0,
          break_even_price: Math.round(break_even_price * 100) / 100
        }
      }
      
      case 'target_profit': {
        const target = input.target_value || 0
        const required_price = (target + f) / (1 - v)
        
        return {
          required_price: Math.round(required_price * 100) / 100,
          net_profit: target,
          net_margin: Math.round((target / required_price) * 10000) / 10000,
          is_loss: false,
          is_feasible: true,
          break_even_price: Math.round((f / (1 - v)) * 100) / 100
        }
      }
      
      case 'target_margin': {
        const target_margin = input.target_value || 0
        const feasible = target_margin < (1 - v)
        const required_price = feasible ? f / (1 - v - target_margin) : Infinity
        
        return {
          required_price: Math.round(required_price * 100) / 100,
          net_profit: feasible ? Math.round((required_price * target_margin) * 100) / 100 : 0,
          net_margin: target_margin,
          is_loss: false,
          is_feasible: feasible,
          break_even_price: Math.round((f / (1 - v)) * 100) / 100
        }
      }
      
      case 'target_roi': {
        const target_roi = input.target_value || 0
        const cost = f / (1 - v)
        const required_price = cost * (1 + target_roi)
        
        return {
          required_price: Math.round(required_price * 100) / 100,
          net_profit: Math.round((required_price - cost) * 100) / 100,
          net_margin: Math.round((target_roi / (1 + target_roi)) * 10000) / 10000,
          is_loss: false,
          is_feasible: true,
          break_even_price: Math.round(cost * 100) / 100
        }
      }
      
      default:
        return {
          net_profit: 0,
          net_margin: 0,
          is_loss: false,
          break_even_price: 0
        }
    }
  }
  
  // 计算变量费率总和
  const calculateVariableRate = () => {
    return (
      costBreakdown.platform_commission_rate +
      costBreakdown.payment_fee_rate +
      costBreakdown.tax_rate +
      costBreakdown.ad_rate +
      costBreakdown.exchange_loss_rate
    )
  }
  
  // 计算固定成本总和
  const calculateFixedCost = () => {
    return (
      costBreakdown.purchase_cost +
      costBreakdown.logistics_cost +
      costBreakdown.packaging_cost +
      costBreakdown.fulfillment_cost +
      costBreakdown.storage_cost +
      costBreakdown.last_mile_cost +
      costBreakdown.ad_allocation +
      costBreakdown.return_loss +
      costBreakdown.cancel_loss +
      costBreakdown.promotion_subsidy +
      costBreakdown.other_cost
    )
  }
  
  // 执行计算
  const handleCalculate = () => {
    form.validateFields().then(values => {
      const variable_rate_total = calculateVariableRate()
      const fixed_cost_total = calculateFixedCost()
      
      const input: ProfitInput = {
        mode: calculationMode as any,
        sale_price: values.sale_price,
        list_price: values.sale_price || 200,
        variable_rate_total,
        fixed_cost_total,
        target_value: values.target_value
      }
      
      setProfitInput(input)
      message.success('计算完成！')
    })
  }
  
  // 成本拆分表格列
  const costColumns = [
    {
      title: '费用项',
      dataIndex: 'name',
      key: 'name'
    },
    {
      title: '金额/比率',
      dataIndex: 'value',
      key: 'value',
      render: (value: number, record: any) => 
        record.type === 'rate' ? `${(value * 100).toFixed(1)}%` : `¥${value.toFixed(2)}`
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description'
    }
  ]
  
  // 变量费率数据
  const variableRateData = [
    {
      name: '平台佣金率',
      value: costBreakdown.platform_commission_rate,
      description: 'Ozon平台佣金',
      type: 'rate'
    },
    {
      name: '支付费率',
      value: costBreakdown.payment_fee_rate,
      description: '支付手续费',
      type: 'rate'
    },
    {
      name: '税费率',
      value: costBreakdown.tax_rate,
      description: '增值税等',
      type: 'rate'
    },
    {
      name: '广告费率',
      value: costBreakdown.ad_rate,
      description: '按销售额分摊',
      type: 'rate'
    },
    {
      name: '汇损费率',
      value: costBreakdown.exchange_loss_rate,
      description: '汇率损失',
      type: 'rate'
    }
  ]
  
  // 固定成本数据
  const fixedCostData = [
    {
      name: '采购成本',
      value: costBreakdown.purchase_cost,
      description: '商品成本',
      type: 'cost'
    },
    {
      name: '头程物流',
      value: costBreakdown.logistics_cost,
      description: '中国→俄罗斯',
      type: 'cost'
    },
    {
      name: '包材',
      value: costBreakdown.packaging_cost,
      description: '包装材料',
      type: 'cost'
    },
    {
      name: '履约费',
      value: costBreakdown.fulfillment_cost,
      description: '拣货、打包、发货',
      type: 'cost'
    },
    {
      name: '仓储费',
      value: costBreakdown.storage_cost,
      description: '仓库存储',
      type: 'cost'
    },
    {
      name: '尾程物流',
      value: costBreakdown.last_mile_cost,
      description: '俄罗斯境内配送',
      type: 'cost'
    },
    {
      name: '广告分摊',
      value: costBreakdown.ad_allocation,
      description: '广告费用/订单数',
      type: 'cost'
    },
    {
      name: '退货损失',
      value: costBreakdown.return_loss,
      description: '退货率 × 单次退货损失',
      type: 'cost'
    },
    {
      name: '取消损失',
      value: costBreakdown.cancel_loss,
      description: '取消率 × 单次取消损失',
      type: 'cost'
    },
    {
      name: '促销补贴',
      value: costBreakdown.promotion_subsidy,
      description: '促销成本/销量',
      type: 'cost'
    },
    {
      name: '其他成本',
      value: costBreakdown.other_cost,
      description: '其他成本',
      type: 'cost'
    }
  ]
  
  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      <Title level={2}>
        <CalculatorOutlined /> 利润求解器
      </Title>
      <Paragraph type="secondary">
        多口径净利润计算与求解，支持4种求解模式、成本拆分、折扣模拟
      </Paragraph>
      
      <Row gutter={16}>
        {/* 左侧：输入表单 */}
        <Col span={12}>
          <Card title="输入参数" extra={<Tag color="blue">V5.1</Tag>}>
            <Form form={form} layout="vertical">
              {/* 求解模式选择 */}
              <Form.Item label="求解模式" required>
                <Select
                  value={calculationMode}
                  onChange={setCalculationMode}
                  options={[
                    { label: '计算当前净利润', value: 'current' },
                    { label: '目标利润反推售价', value: 'target_profit' },
                    { label: '目标净利率反推售价', value: 'target_margin' },
                    { label: '目标ROI反推售价', value: 'target_roi' }
                  ]}
                />
              </Form.Item>
              
              {/* 根据模式显示不同输入 */}
              {calculationMode === 'current' && (
                <Form.Item
                  label="售价"
                  name="sale_price"
                  rules={[{ required: true, message: '请输入售价' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    prefix="¥"
                    placeholder="例如: 200"
                    min={0}
                  />
                </Form.Item>
              )}
              
              {calculationMode === 'target_profit' && (
                <Form.Item
                  label="目标净利润"
                  name="target_value"
                  rules={[{ required: true, message: '请输入目标净利润' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    prefix="¥"
                    placeholder="例如: 20"
                  />
                </Form.Item>
              )}
              
              {calculationMode === 'target_margin' && (
                <Form.Item
                  label="目标净利率"
                  name="target_value"
                  rules={[{ required: true, message: '请输入目标净利率' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    suffix="%"
                    placeholder="例如: 15"
                    min={0}
                    max={100}
                  />
                </Form.Item>
              )}
              
              {calculationMode === 'target_roi' && (
                <Form.Item
                  label="目标ROI"
                  name="target_value"
                  rules={[{ required: true, message: '请输入目标ROI' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="例如: 2.0 (代表200% ROI)"
                    min={0}
                    step={0.1}
                  />
                </Form.Item>
              )}
              
              <Divider />
              
              {/* 成本汇总 */}
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="变量费率总和 (V)"
                    value={(calculateVariableRate() * 100).toFixed(1)}
                    suffix="%"
                    precision={1}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="固定成本总和 (F)"
                    value={calculateFixedCost()}
                    prefix="¥"
                    precision={2}
                  />
                </Col>
              </Row>
              
              <Divider />
              
              {/* 高级设置（成本拆分） */}
              <Button
                type="link"
                icon={<SettingOutlined />}
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? '收起' : '展开'}成本拆分
              </Button>
              
              {showAdvanced && (
                <div style={{ marginTop: 16 }}>
                  <Alert
                    message="成本拆分工具"
                    description="根据实际情况调整各项费率和成本，系统会自动计算总和"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Collapse accordion>
                    <Panel header="变量费率设置" key="1">
                      <Form.Item label="平台佣金率">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.platform_commission_rate}
                          onChange={(v) => setCostBreakdown({...costBreakdown, platform_commission_rate: v || 0})}
                          min={0}
                          max={1}
                          step={0.01}
                        />
                      </Form.Item>
                      <Form.Item label="支付费率">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.payment_fee_rate}
                          onChange={(v) => setCostBreakdown({...costBreakdown, payment_fee_rate: v || 0})}
                          min={0}
                          max={1}
                          step={0.01}
                        />
                      </Form.Item>
                      <Form.Item label="税费率">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.tax_rate}
                          onChange={(v) => setCostBreakdown({...costBreakdown, tax_rate: v || 0})}
                          min={0}
                          max={1}
                          step={0.01}
                        />
                      </Form.Item>
                      <Form.Item label="广告费率">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.ad_rate}
                          onChange={(v) => setCostBreakdown({...costBreakdown, ad_rate: v || 0})}
                          min={0}
                          max={1}
                          step={0.01}
                        />
                      </Form.Item>
                      <Form.Item label="汇损费率">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.exchange_loss_rate}
                          onChange={(v) => setCostBreakdown({...costBreakdown, exchange_loss_rate: v || 0})}
                          min={0}
                          max={1}
                          step={0.01}
                        />
                      </Form.Item>
                    </Panel>
                    
                    <Panel header="固定成本设置" key="2">
                      <Form.Item label="采购成本">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.purchase_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, purchase_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="头程物流">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.logistics_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, logistics_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="包材">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.packaging_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, packaging_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="履约费">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.fulfillment_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, fulfillment_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="仓储费">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.storage_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, storage_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="尾程物流">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.last_mile_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, last_mile_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="广告分摊">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.ad_allocation}
                          onChange={(v) => setCostBreakdown({...costBreakdown, ad_allocation: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="退货损失">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.return_loss}
                          onChange={(v) => setCostBreakdown({...costBreakdown, return_loss: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="取消损失">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.cancel_loss}
                          onChange={(v) => setCostBreakdown({...costBreakdown, cancel_loss: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="促销补贴">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.promotion_subsidy}
                          onChange={(v) => setCostBreakdown({...costBreakdown, promotion_subsidy: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                      <Form.Item label="其他成本">
                        <InputNumber
                          style={{ width: '100%' }}
                          value={costBreakdown.other_cost}
                          onChange={(v) => setCostBreakdown({...costBreakdown, other_cost: v || 0})}
                          min={0}
                          prefix="¥"
                        />
                      </Form.Item>
                    </Panel>
                  </Collapse>
                </div>
              )}
              
              <Divider />
              
              {/* 计算按钮 */}
              <Button
                type="primary"
                size="large"
                icon={<CalculatorOutlined />}
                onClick={handleCalculate}
                loading={isLoading}
                block
              >
                立即计算
              </Button>
            </Form>
          </Card>
        </Col>
        
        {/* 右侧：计算结果 */}
        <Col span={12}>
          <Card title="计算结果">
            {profitResult ? (
              <div>
                {/* 核心指标 */}
                <Row gutter={[16, 16]}>
                  {profitResult.required_price && (
                    <Col span={12}>
                      <Statistic
                        title="建议售价"
                        value={profitResult.required_price}
                        prefix="¥"
                        precision={2}
                        valueStyle={{ color: '#1890ff', fontSize: '28px' }}
                      />
                    </Col>
                  )}
                  
                  <Col span={12}>
                    <Statistic
                      title="净利润"
                      value={profitResult.net_profit}
                      prefix="¥"
                      precision={2}
                      valueStyle={{
                        color: profitResult.is_loss ? '#f5222d' : '#52c41a',
                        fontSize: '28px'
                      }}
                      suffix={profitResult.is_loss && <CloseCircleOutlined />}
                    />
                  </Col>
                  
                  <Col span={12}>
                    <Statistic
                      title="净利率"
                      value={(profitResult.net_margin * 100).toFixed(2)}
                      suffix="%"
                      valueStyle={{ fontSize: '24px' }}
                    />
                    <Progress
                      percent={profitResult.net_margin * 100}
                      showInfo={false}
                      strokeColor={profitResult.net_margin > 0.1 ? '#52c41a' : '#faad14'}
                    />
                  </Col>
                  
                  <Col span={12}>
                    <Statistic
                      title="保本价"
                      value={profitResult.break_even_price}
                      prefix="¥"
                      precision={2}
                      valueStyle={{ color: '#722ed1', fontSize: '24px' }}
                    />
                  </Col>
                </Row>
                
                <Divider />
                
                {/* 状态提示 */}
                {profitResult.is_loss && calculationMode === 'current' && (
                  <Alert
                    message="⚠️ 当前处于亏损状态"
                    description={`售价需达到 ¥${profitResult.break_even_price.toFixed(2)} 才能保本`}
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}
                
                {!profitResult.is_feasible && calculationMode === 'target_margin' && (
                  <Alert
                    message="❌ 目标净利率不可行"
                    description="目标净利率过高，超过了可接受范围"
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}
                
                {profitResult.is_feasible && calculationMode === 'target_margin' && (
                  <Alert
                    message="✅ 目标可实现"
                    description={`需将售价调整为 ¥${profitResult.required_price?.toFixed(2)}`}
                    type="success"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}
                
                {/* 成本详情 */}
                <Collapse ghost>
                  <Panel header="查看成本明细" key="1">
                    <Table
                      dataSource={variableRateData}
                      columns={costColumns}
                      pagination={false}
                      size="small"
                      rowKey="name"
                    />
                    <Divider />
                    <Table
                      dataSource={fixedCostData}
                      columns={costColumns}
                      pagination={false}
                      size="small"
                      rowKey="name"
                    />
                  </Panel>
                </Collapse>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '48px 0' }}>
                <CalculatorOutlined style={{ fontSize: '64px', color: '#d9d9d9' }} />
                <Paragraph type="secondary" style={{ marginTop: 24 }}>
                  请输入参数并点击"立即计算"
                </Paragraph>
              </div>
            )}
          </Card>
          
          {/* 折扣模拟 */}
          {profitResult && calculationMode === 'current' && (
            <Card title="折扣模拟" style={{ marginTop: 16 }}>
              <Alert
                message="模拟不同折扣力度下的利润影响"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
              <Table
                dataSource={[
                  { discount: '95折', price: (form.getFieldValue('sale_price') || 200) * 0.95 },
                  { discount: '9折', price: (form.getFieldValue('sale_price') || 200) * 0.9 },
                  { discount: '85折', price: (form.getFieldValue('sale_price') || 200) * 0.85 },
                  { discount: '8折', price: (form.getFieldValue('sale_price') || 200) * 0.8 }
                ].map(item => {
                  const net_profit = item.price * (1 - calculateVariableRate()) - calculateFixedCost()
                  return {
                    key: item.discount,
                    discount: item.discount,
                    price: item.price,
                    net_profit: net_profit,
                    is_loss: net_profit < 0
                  }
                })}
                columns={[
                  { title: '折扣', dataIndex: 'discount', key: 'discount' },
                  {
                    title: '售价',
                    dataIndex: 'price',
                    key: 'price',
                    render: (v) => `¥${v.toFixed(2)}`
                  },
                  {
                    title: '净利润',
                    dataIndex: 'net_profit',
                    key: 'net_profit',
                    render: (v, record) => (
                      <Text type={record.is_loss ? 'danger' : 'success'}>
                        ¥{v.toFixed(2)} {record.is_loss ? '⛔️' : '✓'}
                      </Text>
                    )
                  }
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}
