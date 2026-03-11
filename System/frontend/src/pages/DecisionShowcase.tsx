import React, { useState } from 'react'
import {
  Box,
  Card,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Chip,
  Button,
  Alert,
  Grid,
  LinearProgress,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Badge,
  Paper,
  Stack
} from '@mui/material'
import {
  AlertTriangle,
  TrendingUp,
  Package,
  DollarSign,
  Target,
  CheckCircle,
  Clock,
  ArrowRight,
  Bell,
  X,
  ChevronRight,
  Eye,
  PlayArrow
} from '@mui/icons-material'

// 示例数据
const mockStrategies = [
  {
    priority: 'P0',
    sku: 'HAA132-01',
    type: '库存',
    issue: '库存仅剩 3 天销量',
    suggestion: '立即补货，联系供应商',
    impact: '预计 3 天后断货，损失 ¥2,340/天',
    status: '待处理'
  },
  {
    priority: 'P0',
    sku: 'LADY-089',
    type: '定价',
    issue: '净利率 -5%，处于亏损状态',
    suggestion: '提高售价 15% 或降低成本',
    impact: '每单亏损 ¥10',
    status: '待处理'
  },
  {
    priority: 'P1',
    sku: 'HBB256-03',
    type: '转化',
    issue: 'CTR 仅 1.2%，低于平均 2.1%',
    suggestion: '优化主图，测试新标题',
    impact: '流量浪费，转化潜力未释放',
    status: '进行中'
  },
  {
    priority: 'P1',
    sku: 'TOY-445',
    type: '广告',
    issue: 'ROAS = 1.5，广告效率低',
    suggestion: '降投低效关键词，提高精准度',
    impact: '广告投入产出比低',
    status: '进行中'
  },
  {
    priority: 'P2',
    sku: 'ELEC-023',
    type: '风控',
    issue: '评分 4.2，较上月下降 0.3',
    suggestion: '排查差评原因，优化产品质量',
    impact: '长期影响转化率',
    status: '待处理'
  },
  {
    priority: 'P3',
    sku: 'HOME-567',
    type: '库存',
    issue: '库存积压，可销天数 90 天',
    suggestion: '降价促销，清理库存',
    impact: '资金占用，仓储成本增加',
    status: '已完成'
  }
]

const mockMetrics = [
  { sku: 'HAA132-01', ctr: 2.3, conversion: 4.2, rating: 4.6, roas: 3.2, daysOfSupply: 3 },
  { sku: 'HBB256-03', ctr: 1.2, conversion: 2.8, rating: 4.3, roas: 2.1, daysOfSupply: 15 },
  { sku: 'LADY-089', ctr: 2.8, conversion: 3.5, rating: 4.1, roas: 1.8, daysOfSupply: 8 },
  { sku: 'TOY-445', ctr: 1.9, conversion: 3.2, rating: 4.7, roas: 1.5, daysOfSupply: 22 },
  { sku: 'ELEC-023', ctr: 2.5, conversion: 4.0, rating: 4.2, roas: 2.8, daysOfSupply: 18 }
]

export default function DecisionShowcase() {
  const [selectedStrategy, setSelectedStrategy] = useState<any>(null)
  const [showAlert, setShowAlert] = useState(true)

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P0': return 'error'
      case 'P1': return 'warning'
      case 'P2': return 'info'
      case 'P3': return 'success'
      default: return 'default'
    }
  }

  const getPriorityBgColor = (priority: string) => {
    switch (priority) {
      case 'P0': return '#ffebee'
      case 'P1': return '#fff3e0'
      case 'P2': return '#e3f2fd'
      case 'P3': return '#f1f8e9'
      default: return '#fafafa'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case '待处理': return <Clock color="error" />
      case '进行中': return <PlayArrow color="warning" />
      case '已完成': return <CheckCircle color="success" />
      default: return null
    }
  }

  const getMetricStatus = (value: number, type: string) => {
    const thresholds: any = {
      ctr: { good: 2.0, bad: 1.5 },
      conversion: { good: 3.5, bad: 2.5 },
      rating: { good: 4.5, bad: 4.0 },
      roas: { good: 2.0, bad: 1.5 },
      daysOfSupply: { good: 14, bad: 7 }
    }
    
    const threshold = thresholds[type]
    if (!threshold) return 'normal'
    
    if (type === 'daysOfSupply') {
      if (value < threshold.bad) return 'critical'
      if (value < threshold.good) return 'warning'
      return 'good'
    }
    
    if (value >= threshold.good) return 'good'
    if (value >= threshold.bad) return 'warning'
    return 'critical'
  }

  const healthScore = 75
  const p0Count = mockStrategies.filter(s => s.priority === 'P0').length
  const p1Count = mockStrategies.filter(s => s.priority === 'P1').length

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 'bold' }}>
        🎯 智能决策引擎 - 展示效果
      </Typography>

      {/* 4. 紧急行动提示 */}
      {showAlert && (
        <Alert
          severity="error"
          icon={<Bell />}
          action={
            <IconButton color="inherit" size="small" onClick={() => setShowAlert(false)}>
              <X />
            </IconButton>
          }
          sx={{ mb: 3 }}
        >
          <Typography variant="h6" gutterBottom>
            🚨 检测到 {p0Count} 个 P0 级别紧急问题
          </Typography>
          <Box>
            {mockStrategies.filter(s => s.priority === 'P0').map((s, i) => (
              <Box key={i} sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip label={s.priority} color="error" size="small" />
                <Typography variant="body2">
                  <strong>{s.sku}</strong> - {s.issue}
                </Typography>
                <Button size="small" variant="contained" color="error">
                  立即处理
                </Button>
              </Box>
            ))}
          </Box>
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* 左侧：健康度评分 + 关键指标 */}
        <Grid item xs={12} md={4}>
          {/* 健康度评分 */}
          <Card sx={{ p: 3, mb: 3, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              🏥 健康度评分
            </Typography>
            <Box sx={{ position: 'relative', display: 'inline-block', my: 3 }}>
              <CircularProgress
                variant="determinate"
                value={healthScore}
                size={150}
                thickness={8}
                sx={{ color: healthScore >= 80 ? '#4caf50' : healthScore >= 60 ? '#ff9800' : '#f44336' }}
              />
              <Box
                sx={{
                  top: 0,
                  left: 0,
                  bottom: 0,
                  right: 0,
                  position: 'absolute',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography variant="h3" component="div" fontWeight="bold">
                  {healthScore}
                </Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary">
              {healthScore >= 80 ? '健康' : healthScore >= 60 ? '良好' : '需要关注'}
            </Typography>
          </Card>

          {/* 统计卡片 */}
          <Card sx={{ p: 2, mb: 3 }}>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#e3f2fd', borderRadius: 2 }}>
                  <Typography variant="h4" color="primary" fontWeight="bold">
                    150
                  </Typography>
                  <Typography variant="body2">总 SKU</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#ffebee', borderRadius: 2 }}>
                  <Typography variant="h4" color="error" fontWeight="bold">
                    {p0Count}
                  </Typography>
                  <Typography variant="body2">紧急问题</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#fff3e0', borderRadius: 2 }}>
                  <Typography variant="h4" color="warning.main" fontWeight="bold">
                    {p1Count}
                  </Typography>
                  <Typography variant="body2">严重问题</Typography>
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#f1f8e9', borderRadius: 2 }}>
                  <Typography variant="h4" color="success.main" fontWeight="bold">
                    1
                  </Typography>
                  <Typography variant="body2">已完成</Typography>
                </Box>
              </Grid>
            </Grid>
          </Card>
        </Grid>

        {/* 右侧：1. 优先级策略清单 */}
        <Grid item xs={12} md={8}>
          <Card sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                📋 1. 优先级策略清单
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Chip label="全部" color="primary" size="small" />
                <Chip label="P0" color="error" size="small" variant="outlined" />
                <Chip label="P1" color="warning" size="small" variant="outlined" />
                <Chip label="P2" color="info" size="small" variant="outlined" />
                <Chip label="P3" color="success" size="small" variant="outlined" />
              </Box>
            </Box>

            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>优先级</TableCell>
                  <TableCell>SKU</TableCell>
                  <TableCell>类型</TableCell>
                  <TableCell>问题描述</TableCell>
                  <TableCell>建议操作</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mockStrategies.map((strategy, index) => (
                  <TableRow
                    key={index}
                    sx={{
                      bgcolor: getPriorityBgColor(strategy.priority),
                      '&:hover': { bgcolor: getPriorityBgColor(strategy.priority), opacity: 0.8 }
                    }}
                  >
                    <TableCell>
                      <Chip
                        label={strategy.priority}
                        color={getPriorityColor(strategy.priority) as any}
                        size="small"
                        icon={<AlertTriangle />}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {strategy.sku}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={strategy.type} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{strategy.issue}</Typography>
                      <Typography variant="caption" color="error">
                        {strategy.impact}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{strategy.suggestion}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(strategy.status) as any}
                        label={strategy.status}
                        size="small"
                        color={strategy.status === '已完成' ? 'success' : strategy.status === '进行中' ? 'warning' : 'error'}
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => setSelectedStrategy(strategy)}
                      >
                        <Eye />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </Grid>
      </Grid>

      {/* 3. 观察指标跟踪 */}
      <Card sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          📊 3. 观察指标跟踪
        </Typography>
        
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>SKU</TableCell>
              <TableCell align="center">CTR</TableCell>
              <TableCell align="center">转化率</TableCell>
              <TableCell align="center">评分</TableCell>
              <TableCell align="center">ROAS</TableCell>
              <TableCell align="center">库存天数</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {mockMetrics.map((metric, index) => (
              <TableRow key={index}>
                <TableCell>
                  <Typography variant="body2" fontWeight="bold">
                    {metric.sku}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <MetricBadge value={metric.ctr} unit="%" status={getMetricStatus(metric.ctr, 'ctr')} />
                </TableCell>
                <TableCell align="center">
                  <MetricBadge value={metric.conversion} unit="%" status={getMetricStatus(metric.conversion, 'conversion')} />
                </TableCell>
                <TableCell align="center">
                  <MetricBadge value={metric.rating} status={getMetricStatus(metric.rating, 'rating')} />
                </TableCell>
                <TableCell align="center">
                  <MetricBadge value={metric.roas} status={getMetricStatus(metric.roas, 'roas')} />
                </TableCell>
                <TableCell align="center">
                  <MetricBadge value={metric.daysOfSupply} unit="天" status={getMetricStatus(metric.daysOfSupply, 'daysOfSupply')} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* 2. 具体执行建议弹窗 */}
      <Dialog
        open={!!selectedStrategy}
        onClose={() => setSelectedStrategy(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedStrategy && (
          <>
            <DialogTitle sx={{ bgcolor: getPriorityBgColor(selectedStrategy.priority) }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Chip
                  label={selectedStrategy.priority}
                  color={getPriorityColor(selectedStrategy.priority) as any}
                  icon={<AlertTriangle />}
                />
                <Typography variant="h6">
                  {selectedStrategy.sku} - {selectedStrategy.issue}
                </Typography>
              </Box>
            </DialogTitle>
            <DialogContent sx={{ pt: 3 }}>
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                  📊 问题诊断
                </Typography>
                <Paper sx={{ p: 2, bgcolor: '#f5f5f5' }}>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        问题类型
                      </Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {selectedStrategy.type}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="text.secondary">
                        影响范围
                      </Typography>
                      <Typography variant="body1" fontWeight="bold" color="error">
                        {selectedStrategy.impact}
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              </Box>

              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                🎯 执行建议（优先级排序）
              </Typography>

              <List>
                {selectedStrategy.priority === 'P0' && (
                  <>
                    <ListItem>
                      <ListItemIcon>
                        <Badge badgeContent="1" color="error">
                          <Clock color="error" />
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary="立即行动（1 小时内）"
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              1. 联系供应商确认交期
                            </Typography>
                            <Typography variant="body2">
                              2. 调整店铺设置，降低预计发货时间
                            </Typography>
                            <Typography variant="body2">
                              3. 设置库存预警为 10 件
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider />
                    <ListItem>
                      <ListItemIcon>
                        <Badge badgeContent="2" color="warning">
                          <TrendingUp color="warning" />
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary="短期优化（24 小时内）"
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              1. 降低广告预算 30%
                            </Typography>
                            <Typography variant="body2">
                              2. 暂停高花费关键词
                            </Typography>
                            <Typography variant="body2">
                              3. 保留品牌词广告
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider />
                    <ListItem>
                      <ListItemIcon>
                        <Badge badgeContent="3" color="success">
                          <Target color="success" />
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary="中长期预防（7 天内）"
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              1. 与供应商签订安全库存协议
                            </Typography>
                            <Typography variant="body2">
                              2. 设置自动补货规则（库存 &lt; 100 件触发）
                            </Typography>
                            <Typography variant="body2">
                              3. 考虑备选供应商
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  </>
                )}

                {selectedStrategy.priority === 'P1' && (
                  <>
                    <ListItem>
                      <ListItemIcon>
                        <Badge badgeContent="1" color="primary">
                          <Target color="primary" />
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary="Step 1: 主图优化（3 天测试）"
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              • 使用纯白背景 + 45° 角度拍摄
                            </Typography>
                            <Typography variant="body2">
                              • 添加使用场景图
                            </Typography>
                            <Typography variant="body2">
                              • 标注核心卖点
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider />
                    <ListItem>
                      <ListItemIcon>
                        <Badge badgeContent="2" color="primary">
                          <Target color="primary" />
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary="Step 2: 标题优化（5 天测试）"
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              建议标题 A: "静音落地扇 | 3档风速 | 遥控控制 | 夏季必备"
                            </Typography>
                            <Typography variant="body2">
                              建议标题 B: "智能落地扇 | 直流变频 | 超静音 | 一键预约"
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider />
                    <ListItem>
                      <ListItemIcon>
                        <Badge badgeContent="3" color="primary">
                          <Target color="primary" />
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary="Step 3: 价格测试（7 天观察）"
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              • 当前价格: ¥299
                            </Typography>
                            <Typography variant="body2">
                              • 测试价格: ¥279（限时 3 天）
                            </Typography>
                            <Typography variant="body2">
                              • 观察 CTR 和转化率变化
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  </>
                )}
              </List>

              <Box sx={{ mt: 3, p: 2, bgcolor: '#e3f2fd', borderRadius: 2 }}>
                <Typography variant="subtitle2" color="primary" gutterBottom fontWeight="bold">
                  💰 预期收益
                </Typography>
                <Typography variant="body2">
                  • 避免断货损失: ¥2,340/天 × 2 天 = ¥4,680
                </Typography>
                <Typography variant="body2">
                  • 保护店铺权重: 预计影响搜索排名 -5%
                </Typography>
                <Typography variant="body2">
                  • 客户满意度: 避免约 24 个订单延迟
                </Typography>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedStrategy(null)}>关闭</Button>
              <Button variant="contained" color="primary" startIcon={<CheckCircle />}>
                标记为已处理
              </Button>
              <Button variant="outlined" startIcon={<PlayArrow />}>
                开始执行
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  )
}

// 辅助组件：指标徽章
function MetricBadge({ value, unit = '', status }: { value: number; unit?: string; status: string }) {
  const getColor = () => {
    switch (status) {
      case 'good': return '#4caf50'
      case 'warning': return '#ff9800'
      case 'critical': return '#f44336'
      default: return '#9e9e9e'
    }
  }

  const getIcon = () => {
    switch (status) {
      case 'good': return '✓'
      case 'warning': return '⚠️'
      case 'critical': return '⛔'
      default: return ''
    }
  }

  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 1,
        px: 2,
        py: 1,
        borderRadius: 2,
        bgcolor: status === 'good' ? '#f1f8e9' : status === 'warning' ? '#fff3e0' : '#ffebee',
        border: `2px solid ${getColor()}`
      }}
    >
      <Typography variant="body2" fontWeight="bold" sx={{ color: getColor() }}>
        {value}{unit} {getIcon()}
      </Typography>
    </Box>
  )
}

// 简化版 CircularProgress（避免导入整个 MUI）
function CircularProgress({ variant, value, size, thickness, sx }: any) {
  const radius = (size - thickness) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (value / 100) * circumference

  return (
    <Box sx={{ position: 'relative', display: 'inline-flex' }}>
      <svg width={size} height={size}>
        <circle
          stroke="#e0e0e0"
          fill="transparent"
          strokeWidth={thickness}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          stroke="currentColor"
          fill="transparent"
          strokeWidth={thickness}
          strokeLinecap="round"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          style={{
            strokeDasharray: circumference,
            strokeDashoffset: offset,
            transform: 'rotate(-90deg)',
            transformOrigin: '50% 50%',
            transition: 'stroke-dashoffset 0.5s ease'
          }}
          sx={sx}
        />
      </svg>
    </Box>
  )
}
