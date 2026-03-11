import { Card, Button, Alert, Descriptions, Tag } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { dashboardApi, healthCheck } from '../services/api'

export default function ApiTest() {
  const [testResults, setTestResults] = useState<any>({})
  const [testing, setTesting] = useState(false)

  const runTests = async () => {
    setTesting(true)
    const results: any = {}

    // 测试1: 健康检查
    try {
      const health = await healthCheck()
      results.health = { success: true, data: health }
    } catch (error) {
      results.health = { success: false, error: String(error) }
    }

    // 测试2: Dashboard 指标
    try {
      const metrics = await dashboardApi.getMetrics()
      results.metrics = { success: true, data: metrics }
    } catch (error) {
      results.metrics = { success: false, error: String(error) }
    }

    // 测试3: Top SKUs
    try {
      const topSkus = await dashboardApi.getTopSkus()
      results.topSkus = { success: true, data: topSkus }
    } catch (error) {
      results.topSkus = { success: false, error: String(error) }
    }

    // 测试4: 告警
    try {
      const alerts = await dashboardApi.getAlerts()
      results.alerts = { success: true, data: alerts }
    } catch (error) {
      results.alerts = { success: false, error: String(error) }
    }

    setTestResults(results)
    setTesting(false)
  }

  const allPassed = Object.values(testResults).every((r: any) => r?.success)

  return (
    <div style={{ padding: 24 }}>
      <Card title="API 连接测试" extra={
        <Button type="primary" onClick={runTests} loading={testing}>
          运行测试
        </Button>
      }>
        {Object.keys(testResults).length > 0 && (
          <>
            <Alert
              message={allPassed ? "所有测试通过！API 连接正常" : "部分测试失败，请检查后端服务"}
              type={allPassed ? "success" : "error"}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions bordered column={1}>
              <Descriptions.Item
                label="健康检查 (/api/health)"
              >
                {testResults.health?.success ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    成功
                  </Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    失败: {testResults.health?.error}
                  </Tag>
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Dashboard 指标">
                {testResults.metrics?.success ? (
                  <>
                    <Tag icon={<CheckCircleOutlined />} color="success">成功</Tag>
                    <pre style={{ marginTop: 8, fontSize: 12 }}>
                      {JSON.stringify(testResults.metrics?.data, null, 2)}
                    </pre>
                  </>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    失败: {testResults.metrics?.error}
                  </Tag>
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Top SKUs">
                {testResults.topSkus?.success ? (
                  <>
                    <Tag icon={<CheckCircleOutlined />} color="success">成功</Tag>
                    <pre style={{ marginTop: 8, fontSize: 12 }}>
                      {JSON.stringify(testResults.topSkus?.data, null, 2)}
                    </pre>
                  </>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    失败: {testResults.topSkus?.error}
                  </Tag>
                )}
              </Descriptions.Item>

              <Descriptions.Item label="告警列表">
                {testResults.alerts?.success ? (
                  <>
                    <Tag icon={<CheckCircleOutlined />} color="success">成功</Tag>
                    <pre style={{ marginTop: 8, fontSize: 12 }}>
                      {JSON.stringify(testResults.alerts?.data, null, 2)}
                    </pre>
                  </>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    失败: {testResults.alerts?.error}
                  </Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
          </>
        )}

        {Object.keys(testResults).length === 0 && (
          <Alert
            message="点击"运行测试"按钮开始测试 API 连接"
            type="info"
          />
        )}
      </Card>

      <Card title="使用说明" style={{ marginTop: 16 }}>
        <pre style={{ fontSize: 13 }}>
{`1. 启动后端 API 服务：
   cd C:\\Operation-system\\System
   python run_api.py

2. 确认后端运行：
   访问 http://localhost:5000/api/health

3. 启动前端开发服务器：
   cd frontend
   npm run dev

4. 访问前端：
   http://localhost:5173

5. 测试 API 连接：
   点击上方"运行测试"按钮`}
        </pre>
      </Card>
    </div>
  )
}
