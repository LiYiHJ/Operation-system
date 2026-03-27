import { Suspense, lazy } from 'react'

const ReactECharts = lazy(() => import('echarts-for-react'))

type LazyEChartProps = {
  style?: { height?: number | string }
  [key: string]: unknown
}

function ChartFallback({ height }: { height?: number | string }) {
  const normalizedHeight = typeof height === 'number' ? `${height}px` : (height || '360px')
  return (
    <div
      style={{
        minHeight: normalizedHeight,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#8c8c8c',
        background: '#fafafa',
        border: '1px dashed #d9d9d9',
        borderRadius: 8,
      }}
    >
      图表组件加载中...
    </div>
  )
}

export default function LazyEChart(props: LazyEChartProps) {
  const height = props?.style?.height

  return (
    <Suspense fallback={<ChartFallback height={height} />}>
      <ReactECharts {...(props as any)} />
    </Suspense>
  )
}
