import { useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Form, Input, Row, Select, Space, Switch, Table, Tabs, Tag, message } from 'antd'
import { ReloadOutlined, ApiOutlined, UploadOutlined, SendOutlined } from '@ant-design/icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { integrationApi } from '../services/api'
import DataImportV2 from './DataImportV2'
import { OpsPageHeader } from '../components/ops/ProductSection'

export default function SystemSettings() {
  const [form] = Form.useForm()
  const [pushForm] = Form.useForm()

  const { data: cfg, refetch: refetchCfg } = useQuery({ queryKey: ['integration-config'], queryFn: () => integrationApi.getDataSource({ provider: 'ozon', shopId: 1 }) })
  const { data: syncLogs, refetch: refetchSyncLogs } = useQuery({ queryKey: ['sync-logs'], queryFn: () => integrationApi.getSyncLogs({ shopId: 1, limit: 20 }) })
  const { data: importLogs, refetch: refetchImportLogs } = useQuery({ queryKey: ['import-logs'], queryFn: () => integrationApi.getImportLogs({ shopId: 1, limit: 20 }) })
  const { data: pushLogs, refetch: refetchPushLogs } = useQuery({ queryKey: ['push-logs'], queryFn: () => integrationApi.getPushLogs({ shopId: 1, limit: 20 }) })

  const saveMutation = useMutation({
    mutationFn: (payload: any) => integrationApi.saveDataSource(payload),
    onSuccess: () => { message.success('数据源配置已保存'); refetchCfg() },
    onError: (e: any) => message.error(e.message),
  })

  const syncMutation = useMutation({
    mutationFn: () => integrationApi.syncOnce({ provider: 'ozon', shopId: 1 }),
    onSuccess: (res: any) => { message.success(`同步完成: ${res.status}`); refetchCfg(); refetchSyncLogs(); refetchImportLogs() },
    onError: (e: any) => message.error(`同步失败: ${e.message}`),
  })

  const pushMutation = useMutation({
    mutationFn: (payload: any) => integrationApi.pushSales(payload),
    onSuccess: (res: any) => { message.success(`推送结果: ${res.status}`); refetchPushLogs() },
    onError: (e: any) => message.error(`推送失败: ${e.message}`),
  })

  const initialValues = useMemo(() => ({
    provider: cfg?.provider || 'ozon',
    enabled: !!cfg?.enabled,
    autoSyncEnabled: !!cfg?.autoSyncEnabled,
    syncFrequency: cfg?.syncFrequency || 'manual',
    clientId: cfg?.credentials?.clientId || '',
    apiKey: cfg?.credentials?.apiKey || '',
    sellerId: cfg?.credentials?.sellerId || '',
    salesPushUrl: cfg?.settings?.sales_push_url || 'http://127.0.0.1:5000/api/integration/mock/sales-backend',
  }), [cfg])

  const syncColumns = [
    { title: '时间', dataIndex: 'startedAt', width: 190 },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={v === 'success' ? 'green' : v === 'running' ? 'blue' : 'red'}>{v}</Tag> },
    { title: '导入行数', dataIndex: 'importedRows', width: 90 },
    { title: '批次', dataIndex: 'batchId', width: 80 },
    { title: '信息', dataIndex: 'message', ellipsis: true },
  ]

  const importColumns = [
    { title: '批次', dataIndex: 'batchId', width: 80 },
    { title: '状态', dataIndex: 'status', width: 100, render: (v: string) => <Tag color={v === 'success' ? 'green' : v === 'failed' ? 'red' : 'blue'}>{v}</Tag> },
    { title: '成功', dataIndex: 'successCount', width: 90 },
    { title: '失败', dataIndex: 'errorCount', width: 90 },
    { title: '开始时间', dataIndex: 'startedAt', width: 190 },
    { title: '说明', dataIndex: 'message', ellipsis: true },
  ]

  const pushColumns = [
    { title: '推送ID', dataIndex: 'pushId', width: 90 },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: string) => <Tag color={v === 'success' ? 'green' : 'red'}>{v}</Tag> },
    { title: 'HTTP', dataIndex: 'httpStatus', width: 90 },
    { title: '任务ID', dataIndex: 'strategyTaskId', width: 100 },
    { title: '执行ID', dataIndex: 'executionLogId', width: 110 },
    { title: '推送时间', dataIndex: 'pushedAt', width: 190 },
    { title: '错误', dataIndex: 'error', ellipsis: true },
  ]

  return (
    <div style={{ padding: 24 }}>
      <OpsPageHeader title="⚙️ 系统设置" subtitle="数据接入以 API 自动拉取为主，文件导入为辅。" />
      <Tabs
        defaultActiveKey="access"
        items={[
          {
            key: 'access',
            label: '数据接入',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                <Alert type="info" showIcon message="主接入方式：Ozon API 自动拉取" description="可配置手工同步、自动拉取、最近同步与最近导入记录。" />
                <Card title="Ozon API 配置" extra={<Button icon={<ReloadOutlined />} onClick={() => refetchCfg()}>刷新配置</Button>}>
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
                        credentials: { clientId: values.clientId, apiKey: values.apiKey, sellerId: values.sellerId },
                        settings: { sales_push_url: values.salesPushUrl },
                      })
                    }}
                  >
                    <Row gutter={[12, 12]}>
                      <Col xs={24} lg={8}><Form.Item label="Provider" name="provider"><Input disabled /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="启用数据源" name="enabled" valuePropName="checked"><Switch /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="自动拉取" name="autoSyncEnabled" valuePropName="checked"><Switch /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="同步频率" name="syncFrequency"><Select options={[{ value: 'manual', label: '手动' }, { value: 'hourly', label: '每小时' }, { value: 'daily', label: '每日' }]} /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="Client ID" name="clientId"><Input placeholder="ozon client id" /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="API Key" name="apiKey"><Input.Password placeholder="ozon api key" /></Form.Item></Col>
                      <Col xs={24} lg={8}><Form.Item label="Seller ID" name="sellerId"><Input placeholder="seller id" /></Form.Item></Col>
                      <Col xs={24} lg={16}><Form.Item label="销售后台推送URL" name="salesPushUrl"><Input /></Form.Item></Col>
                    </Row>
                    <Space>
                      <Button type="primary" htmlType="submit" icon={<ApiOutlined />} loading={saveMutation.isPending}>保存配置</Button>
                      <Button icon={<ReloadOutlined />} loading={syncMutation.isPending} onClick={() => syncMutation.mutate()}>立即同步一次</Button>
                    </Space>
                  </Form>
                </Card>

                <Row gutter={[12, 12]}>
                  <Col xs={24} lg={12}><Card title="最近同步记录"><Table rowKey="id" size="small" dataSource={syncLogs?.rows || []} columns={syncColumns as any} pagination={{ pageSize: 5 }} scroll={{ x: 760, y: 280 }} tableLayout="fixed" /></Card></Col>
                  <Col xs={24} lg={12}><Card title="最近导入记录"><Table rowKey="batchId" size="small" dataSource={importLogs?.rows || []} columns={importColumns as any} pagination={{ pageSize: 5 }} scroll={{ x: 820, y: 280 }} tableLayout="fixed" /></Card></Col>
                </Row>
              </Space>
            ),
          },
          {
            key: 'import',
            label: '文件导入',
            children: (
              <Card title="文件导入（备用入口）" extra={<Tag color="blue">文件导入 / API 接入统一在系统设置管理</Tag>}>
                <DataImportV2 />
              </Card>
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
                    initialValues={{ sku: 'SKU-DEMO-001', actionType: 'pricing', actionBefore: 'price=99', actionAfter: 'price=109', sourcePage: 'decision', sourceReason: 'manual_push_test', operator: 'operator' }}
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
