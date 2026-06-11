import { useCallback, useEffect, useState } from 'react'
import {
  Button, Card, Col, Empty, Form, Input, List, Modal, Row, Select, Space, Tag, Typography, message,
} from 'antd'
import { CheckOutlined, CloseOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons'
import { DEFAULT_CATEGORIES, DIFFICULTY_LABELS, Q_TYPE_LABELS, api, type Question } from '../api'

interface Source { source_locator: string; content: string }

export default function Review() {
  const [list, setList] = useState<Question[]>([])
  const [total, setTotal] = useState(0)
  const [current, setCurrent] = useState<Question | null>(null)
  const [source, setSource] = useState<Source | null>(null)
  const [statusFilter, setStatusFilter] = useState('pending_review')
  const [typeFilter, setTypeFilter] = useState<string>()
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES)
  const [subMap, setSubMap] = useState<Record<string, string[]>>({})
  const [form] = Form.useForm()
  const editCategory = Form.useWatch('category', form)

  useEffect(() => {
    api.get('/categories').then((r) => { setCategories(r.data.categories); setSubMap(r.data.subcategories) })
  }, [])

  const load = useCallback(async (selectFirst = true) => {
    const { data } = await api.get('/questions', {
      params: { status: statusFilter, q_type: typeFilter, page_size: 100 },
    })
    setList(data.items); setTotal(data.total)
    if (selectFirst) select(data.items[0] ?? null)
  }, [statusFilter, typeFilter])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const select = async (q: Question | null) => {
    setCurrent(q); setSource(null)
    if (!q) return
    form.setFieldsValue({
      stem: q.stem,
      answer: q.answer,
      analysis: q.analysis,
      difficulty: q.difficulty,
      category: q.category || undefined,
      subcategory: q.subcategory ? [q.subcategory] : [],
      options: (q.options ?? []).map((o) => `${o.key}. ${o.text}`).join('\n'),
    })
    const { data } = await api.get(`/questions/${q.id}`)
    setSource(data.source)
  }

  const parseOptions = (text: string) =>
    text.split('\n').map((l) => l.trim()).filter(Boolean).map((l) => {
      const m = l.match(/^([A-H])[.、:：\s]\s*(.*)$/)
      return m ? { key: m[1], text: m[2] } : null
    }).filter((x): x is { key: string; text: string } => !!x)

  const save = async () => {
    if (!current) return
    const v = form.getFieldsValue()
    const sub = Array.isArray(v.subcategory) ? (v.subcategory[0] ?? '') : (v.subcategory ?? '')
    const body: Record<string, unknown> = {
      stem: v.stem, answer: v.answer, analysis: v.analysis, difficulty: v.difficulty,
      category: v.category ?? '', subcategory: sub,
    }
    if (current.options) body.options = parseOptions(v.options ?? '')
    await api.put(`/questions/${current.id}`, body)
    message.success('已保存修改')
  }

  const advance = () => {
    const idx = list.findIndex((q) => q.id === current?.id)
    const rest = list.filter((q) => q.id !== current?.id)
    setList(rest); setTotal((t) => t - 1)
    select(rest[Math.min(idx, rest.length - 1)] ?? null)
  }

  const approve = async () => {
    if (!current) return
    await save()
    await api.post(`/questions/${current.id}/approve`)
    message.success('已通过，进入标准题库')
    advance()
  }

  const reject = () => {
    if (!current) return
    let reason = ''
    Modal.confirm({
      title: '退回题目',
      content: <Input.TextArea placeholder="退回理由（可选）" onChange={(e) => { reason = e.target.value }} />,
      onOk: async () => {
        await api.post(`/questions/${current.id}/reject`, { reason })
        message.success('已退回')
        advance()
      },
    })
  }

  const remove = async () => {
    if (!current) return
    await api.delete(`/questions/${current.id}`)
    message.success('已删除')
    advance()
  }

  return (
    <div>
      <Typography.Title level={3}>审核工作台 <Typography.Text type="secondary" style={{ fontSize: 14 }}>共 {total} 题</Typography.Text></Typography.Title>
      <Space style={{ marginBottom: 12 }}>
        <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 130 }}
          options={[
            { value: 'pending_review', label: '待审核' },
            { value: 'rejected', label: '已退回' },
          ]} />
        <Select value={typeFilter} onChange={setTypeFilter} allowClear placeholder="全部题型" style={{ width: 130 }}
          options={Object.entries(Q_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
      </Space>
      <Row gutter={16}>
        <Col span={8}>
          <Card size="small" styles={{ body: { maxHeight: '72vh', overflow: 'auto', padding: 0 } }}>
            <List
              size="small" dataSource={list}
              renderItem={(q) => (
                <List.Item
                  onClick={() => select(q)}
                  style={{ cursor: 'pointer', padding: '8px 12px', background: q.id === current?.id ? '#e6f4ff' : undefined }}>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <Space>
                      <Tag>{Q_TYPE_LABELS[q.q_type]}</Tag>
                      <Tag color="default">{DIFFICULTY_LABELS[q.difficulty]}</Tag>
                    </Space>
                    <Typography.Text ellipsis style={{ maxWidth: '100%' }}>{q.stem}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={10}>
          {current ? (
            <Card size="small" title={`题目 #${current.id} — ${Q_TYPE_LABELS[current.q_type]}`}
              extra={current.reject_reason && <Tag color="red">退回理由: {current.reject_reason}</Tag>}>
              <Form form={form} layout="vertical" size="small">
                <Form.Item name="stem" label="题干"><Input.TextArea autoSize={{ minRows: 2 }} /></Form.Item>
                {current.options && (
                  <Form.Item name="options" label="选项（每行一个，格式：A. 内容）">
                    <Input.TextArea autoSize={{ minRows: 2 }} />
                  </Form.Item>
                )}
                <Form.Item name="answer" label="答案"><Input.TextArea autoSize={{ minRows: 1 }} /></Form.Item>
                <Form.Item name="analysis" label="解析"><Input.TextArea autoSize={{ minRows: 2 }} /></Form.Item>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Form.Item name="difficulty" label="难度" style={{ flex: 1 }}>
                    <Select options={Object.entries(DIFFICULTY_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
                  </Form.Item>
                  <Form.Item name="category" label="大类" style={{ flex: 1 }}>
                    <Select allowClear placeholder="未分类" options={categories.map((c) => ({ value: c, label: c }))} />
                  </Form.Item>
                  <Form.Item name="subcategory" label="小类（可空）" style={{ flex: 1 }}>
                    <Select allowClear showSearch mode="tags" maxCount={1} placeholder="可填"
                      options={(subMap[editCategory] ?? []).map((s) => ({ value: s, label: s }))} />
                  </Form.Item>
                </div>
              </Form>
              <Space>
                <Button icon={<SaveOutlined />} onClick={save}>保存</Button>
                <Button type="primary" icon={<CheckOutlined />} onClick={approve}>通过</Button>
                <Button icon={<CloseOutlined />} onClick={reject}>退回</Button>
                <Button danger icon={<DeleteOutlined />} onClick={remove}>删除</Button>
              </Space>
            </Card>
          ) : <Empty description="当前队列没有题目" style={{ marginTop: 80 }} />}
        </Col>
        <Col span={6}>
          <Card size="small" title={source ? `来源原文 — ${source.source_locator}` : '来源原文'}
            styles={{ body: { maxHeight: '68vh', overflow: 'auto' } }}>
            {source
              ? <pre className="ths-code">{source.content}</pre>
              : <Typography.Text type="secondary">选中题目后显示原文片段</Typography.Text>}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
