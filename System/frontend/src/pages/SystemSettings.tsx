import { useMemo, useState } from 'react'
import { Alert, Button, Card, Checkbox, Col, Form, Input, Row, Select, Space, Switch, Table, Tabs, Tag, message } from 'antd'
import { ReloadOutlined, ApiOutlined, SendOutlined, SafetyOutlined, SettingOutlined } from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { integrationApi } from '../services/api'
import { OpsPageHeader } from '../components/ops/ProductSection'

export default function SystemSettings() {
  const [form] = Form.useForm()
  const [pushForm] = Form.useForm()
  const [selectedScopes, setSelectedScopes] = useState<string[]>([])

  const { data: cfg, refetch: refetchCfg } = useQuery({ queryKey: ['integration-config'], queryFn: () => integrationApi.getDataSource({ provider: 'ozon', shopId: 1 }) })
  const { data: syncLogs, refetch: refetchSyncLogs } = useQuery({ queryKey: ['sync-logs'], queryFn: () => integrationApi.getSyncLogs({ shopId: 1, limit: 20 }) })
  const { data: importLogs, refetch: refetchImportLogs } = useQuery({ queryKey: ['import-logs'], queryFn: () => integrationApi.getImportLogs({ shopId: 1, limit: 20 }) })
  const { data: pushLogs, refetch: refetchPushLogs } = useQuery({ queryKey: ['push-logs'], queryFn: () => integrationApi.getPushLogs({ shopId: 1, limit: 20 }) })
  const { data: domains } = useQuery({ queryKey: ['integration-domains'], queryFn: () => integrationApi.getDomains({ shopId: 1 }) })

  const saveMutation = useMutation({
    mutationFn: (payload: any) => integrationApi.saveDataSource(payload),
    onSuccess: () => { message.success('数据源配置已保存'); refetchCfg() },
    onError: (e: any) => message.error(e.message),
  })

  const checkPermissionMutation = useMutation({
    mutationFn: () => integrationApi.checkPermission({ provider: 'ozon', shopId: 1 }),
    onSuccess: (res: any) => message.success(`权限检查完成：只读 Token=${res.readTokenReady ? '已就绪' : '缺失'} / 执行 Token=${res.actionTokenReady ? '已就绪' : '缺失'}`),
    onError: (e: any) => message.error(`权限检查失败: ${e.message}`),
  })

  const syncMutation = useMutation({
    mutationFn: () => integrationApi.syncOnce({ provider: 'ozon', shopId: 1, scopes: selectedScopes.length ? selectedScopes : undefined }),
    onSuccess: (res: any) => { message.success(`同步完成：${res.status === 'success' ? '成功' : res.status === 'failed' ? '失败' : res.status}`); refetchCfg(); refetchSyncLogs(); refetchImportLogs() },
    onError: (e: any) => message.error(`同步失败: ${e.message}`),
  })

  const pushMutation = useMutation({
    mutationFn: (payload: any) => integrationApi.pushSales(payload),
    onSuccess: (res: any) => { message.success(`推送结果：${res.status === 'success' ? '成功' : res.status === 'failed' ? '失败' : res.status}`); refetchPushLogs() },
    onError: (e: any) => message.error(`推送失败: ${e.message}`),
  })

  const initialValues = useMemo(() => ({
    provider: cfg?.provider || 'ozon',
    enabled: !!cfg?.enabled,
    autoSyncEnabled: !!cfg?.autoSyncEnabled,
    syncFrequency: cfg?.syncFrequency || 'manual',
    clientId: cfg?.credentials?.clientId || '',
    readToken: cfg?.credentials?.readToken || '',
    actionToken: cfg?.credentials?.actionToken || '',
    sellerId: cfg?.credentials?.sellerId || '',
    useMockOzon: !!cfg?.settings?.useMockOzon,
    salesPushUrl: cfg?.settings?.sales_push_url || '/api/integration/mock/sales-backend',
  }), [cfg])

  const syncColumns = [
    { title: '时间', dataIndex: 'startedAt', width: 190 },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={v === 'success' ? 'green' : v === 'running' ? 'blue' : 'red'}>{v === 'success' ? '成功' : v === 'running' ? '进行中' : v === 'failed' ? '失败' : v}</Tag> },
    { title: '导入行数', dataIndex: 'importedRows', width: 90 },
    { title: '批次', dataIndex: 'batchId', width: 80 },
    { title: '信息', dataIndex: 'message', ellipsis: true },
  ]

  const importColumns = [
    { title: '批次', dataIndex: 'batchId', width: 80 },
    { title: '状态', dataIndex: 'status', width: 100, render: (v: string) => <Tag color={v === 'success' ? 'green' : v === 'failed' ? 'red' : 'blue'}>{v === 'success' ? '成功' : v === 'failed' ? '失败' : v === 'running' ? '进行中' : v}</Tag> },
    { title: '成功', dataIndex: 'successCount', width: 90 },
    { title: '失败', dataIndex: 'errorCount', width: 90 },
    { title: '开始时间', dataIndex: 'startedAt', width: 190 },
    { title: '说明', dataIndex: 'message', ellipsis: true },
  ]

  const pushColumns = [
    { title: '推送ID', dataIndex: 'pushId', width: 90 },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={v === 'success' ? 'green' : 'red'}>{v === 'success' ? '成功' : v === 'failed' ? '失败' : v}</Tag> },
    { title: 'HTTP', dataIndex: 'httpStatus', width: 90 },
    { title: '任务ID', dataIndex: 'strategyTaskId', width: 100 },
    { title: '执行ID', dataIndex: 'executionLogId', width: 110 },
    { title: '推送时间', dataIndex: 'pushedAt', width: 190 },
    { title: '错误', dataIndex: 'error', ellipsis: true },
  ]

  const domainColumns = [
    { title: '业务域', dataIndex: 'label', width: 220 },
    { title: '权限项', dataIndex: 'permissions', render: (v: string[]) => (v || []).slice(0, 3).join(' / ') + ((v || []).length > 3 ? ' ...' : '') },
    { title: '作用域 Key', dataIndex: 'key', width: 180 },
  ]

  return (
    <div style={{ padding: 24 }}>
      <OpsPageHeader title="⚙️ 系统设置" subtitle="这里仅保留平台连接、同步规则、模板与全局配置；导入执行已迁移到“数据工作台”。" />
      <Tabs
        defaultActiveKey="access"
        type="card"
        items={[
          {
            key: 'access',
            label: '数据接入中心',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                <Alert type="info" showIcon message="主接入方式：Ozon API 自动拉取" description="业务域按 商品、履约、促销、售后、报表 统一管理，避免零散接口堆叠。" />
                <Card title="平台连接与权限" extra={<Button icon={<ReloadOutlined />} onClick={() => refetchCfg()}>刷新配置</Button>}>
                  <Form
                    form={form}
                    layout="vertical"
                    initialValues={initialValues}
                    key={JSON.stringify(initialValues)}
                    onFinish={(values) => {
                      saveMutation.mutate({
                        provider: 'ozon',
                        shopId: 1,
                        enabled: values.enabled,
                        autoSyncEnabled: values.autoSyncEnabled,
                        syncFrequency: values.syncFrequency,
                        credentials: { clientId: values.clientId, readToken: values.readToken, actionToken: values.actionToken, sellerId: values.sellerId },
                        settings: { sales_push_url: values.salesPushUrl, useMockOzon: values.useMockOzon },
                      })
                    }}
                  >
                    <Row gutter={[12, 12]}>
                      <Col xs={24} lg={8}><Form.Item label="Provider" name="provider"><Input disabled /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="启用数据源" name="enabled" valuePropName="checked"><Switch /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="自动拉取" name="autoSyncEnabled" valuePropName="checked"><Switch /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="同步频率" name="syncFrequency"><Select options={[{ value: 'manual', label: '手动' }, { value: 'hourly', label: '每小时' }, { value: 'daily', label: '每日' }]} /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="Client ID" name="clientId"><Input placeholder="请输入 Ozon Client ID" /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="Seller ID" name="sellerId"><Input placeholder="请输入 Seller ID" /></Form.Item></Col>
                      <Col xs={24} lg={12}><Form.Item label="只读采集 Token" name="readToken"><Input.Password placeholder="请输入只读 Token" /></Form.Item></Col>
                      <Col xs={24} lg={12}><Form.Item label="动作执行 Token" name="actionToken"><Input.Password placeholder="请输入执行 Token" /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="使用Mock Ozon（联调）" name="useMockOzon" valuePropName="checked"><Switch /></Form.Item></Col>
                      <Col xs={24} lg={16}><Form.Item label="销售后台推送URL" name="salesPushUrl"><Input /></Form.Item></Col>
                    </Row>
                    <Space>
                      <Button type="primary" htmlType="submit" icon={<ApiOutlined />} loading={saveMutation.isPending}>保存配置</Button>
                      <Button icon={<SafetyOutlined />} loading={checkPermissionMutation.isPending} onClick={() => checkPermissionMutation.mutate()}>权限校验</Button>
                    </Space>
                  </Form>
                </Card>

                <Card title="同步范围（按业务中台）" extra={<Tag color="blue">可多选并立即同步</Tag>}>
                  <Checkbox.Group
                    value={selectedScopes}
                    onChange={(vals) => setSelectedScopes(vals as string[])}
                    options={(domains?.rows || []).map((x: any) => ({ label: x.label, value: x.key }))}
                  />
                  <Space style={{ marginTop: 12 }}>
                    <Button icon={<ReloadOutlined />} loading={syncMutation.isPending} onClick={() => syncMutation.mutate()}>立即同步一次</Button>
                    <Button onClick={() => setSelectedScopes([])}>全量同步</Button>
                  </Space>
                  <Table rowKey="key" style={{ marginTop: 12 }} size="small" dataSource={domains?.rows || []} columns={domainColumns as any} pagination={false} scroll={{ x: 980 }} tableLayout="fixed" />
                </Card>

                <Row gutter={[12, 12]}>
                  <Col xs={24} lg={12}><Card title="最近同步记录"><Table rowKey="id" size="small" dataSource={syncLogs?.rows || []} columns={syncColumns as any} pagination={{ pageSize: 5 }} scroll={{ x: 760, y: 280 }} tableLayout="fixed" /></Card></Col>
                  <Col xs={24} lg={12}><Card title="最近导入记录"><Table rowKey="batchId" size="small" dataSource={importLogs?.rows || []} columns={importColumns as any} pagination={{ pageSize: 5 }} scroll={{ x: 820, y: 280 }} tableLayout="fixed" /></Card></Col>
                </Row>
              </Space>
            ),
          },
          {
            key: 'rules',
            label: '模板与规则',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                <Alert
                  type="info"
                  showIcon
                  message="导入执行已迁移到数据工作台"
                  description="系统设置只保留配置型能力。这里后续承载导入模板、字段映射策略、默认阈值和全局规则维护，不再承载日常导入流程。"
                />
                <Card title="当前规划" extra={<Tag color="blue"><SettingOutlined /> 配置型页面</Tag>}>
                  <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                    <li>字段映射模板维护</li>
                    <li>默认导入 profile/阈值管理</li>
                    <li>平台连接与同步范围配置</li>
                    <li>全局规则与权限设置</li>
                  </ul>
                </Card>
              </Space>
            ),
          },
          {
            key: 'push',
            label: 'API 推送联调',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                <Card title="手工推送测试" extra={<Button icon={<ReloadOutlined />} onClick={() => refetchPushLogs()}>刷新日志</Button>}>
                  <Form
                    form={pushForm}
                    layout="vertical"
                    initialValues={{ sku: 'SKU-DEMO-001', actionType: 'pricing', actionBefore: 'price=99', actionAfter: 'price=109', sourcePage: 'decision', sourceReason: '手工推送联调', operator: 'operator' }}
                    onFinish={(v) => pushMutation.mutate({
                      shopId: 1,
                      payload: {
                        sku: v.sku,
                        actionType: v.actionType,
                        actionBefore: v.actionBefore,
                        actionAfter: v.actionAfter,
                        sourcePage: v.sourcePage,
                        sourceReason: v.sourceReason,
                        operator: v.operator,
                        confirmedAt: new Date().toISOString(),
                      },
                    })}
                  >
                    <Row gutter={[12, 12]}>
                      <Col xs={24} lg={8}><Form.Item label="SKU" name="sku"><Input /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="动作类型" name="actionType"><Select options={[{ value: 'pricing', label: '定价' }, { value: 'inventory', label: '库存' }, { value: 'ads', label: '广告' }]} /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="操作人" name="operator"><Input /></Form.Item></Col>
                      <Col xs={24} lg={12}><Form.Item label="动作前值" name="actionBefore"><Input /></Form.Item></Col>
                      <Col xs={24} lg={12}><Form.Item label="动作后值" name="actionAfter"><Input /></Form.Item></Col>
                      <Col xs={24} lg={12}><Form.Item label="来源页面" name="sourcePage"><Input /></Form.Item></Col>
                      <Col xs={24} lg={12}><Form.Item label="触发原因" name="sourceReason"><Input /></Form.Item></Col>
                    </Row>
                    <Button type="primary" htmlType="submit" icon={<SendOutlined />} loading={pushMutation.isPending}>推送到销售后台 API</Button>
                  </Form>
                </Card>
                <Card title="推送结果日志"><Table rowKey="pushId" dataSource={pushLogs?.rows || []} columns={pushColumns as any} size="small" pagination={{ pageSize: 8 }} scroll={{ x: 980, y: 320 }} tableLayout="fixed" /></Card>
              </Space>
            ),
          },
        ]}
      />
    </div>
  )
}
