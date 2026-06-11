import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Typography } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../api'

interface Stats { documents: number; pending_review: number; approved: number; rejected: number }

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>()
  useEffect(() => { api.get('/stats').then((r) => setStats(r.data)) }, [])
  const cards = [
    { title: '资料总数', value: stats?.documents, link: '/documents' },
    { title: '待审核题目', value: stats?.pending_review, link: '/review' },
    { title: '标准题库', value: stats?.approved, link: '/bank' },
    { title: '已退回', value: stats?.rejected, link: '/review' },
  ]
  return (
    <div>
      <Typography.Title level={3}>工作台</Typography.Title>
      <Row gutter={16}>
        {cards.map((c) => (
          <Col span={6} key={c.title}>
            <Link to={c.link}>
              <Card hoverable><Statistic title={c.title} value={c.value ?? '-'} /></Card>
            </Link>
          </Col>
        ))}
      </Row>
      <Card style={{ marginTop: 24 }} title="使用流程">
        <ol style={{ lineHeight: 2 }}>
          <li>在 <Link to="/documents">资料管理</Link> 上传 PDF / Word / PPT / Excel 培训资料，系统自动解析切片</li>
          <li>在 <Link to="/tasks">生成任务</Link> 选择资料和题型数量，AI 自动出题（题目进入待审核）</li>
          <li>在 <Link to="/review">审核工作台</Link> 对照原文逐题编辑、通过或退回</li>
          <li>在 <Link to="/bank">标准题库</Link> 筛选已通过题目，一键导出组卷系统 Excel 模板</li>
        </ol>
      </Card>
    </div>
  )
}
