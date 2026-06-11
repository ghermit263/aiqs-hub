import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button, Form, InputNumber, Modal, Select, Table, Tag, Typography, message,
} from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { Link, useSearchParams } from 'react-router-dom'
import { DEFAULT_CATEGORIES, Q_TYPE_LABELS, api, type Doc, type Task } from '../api'

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '排队中' },
  running: { color: 'processing', text: '生成中' },
  done: { color: 'success', text: '完成' },
  failed: { color: 'error', text: '失败' },
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [docs, setDocs] = useState<Doc[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const [params, setParams] = useSearchParams()
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES)
  const [subMap, setSubMap] = useState<Record<string, string[]>>({})
  const category = Form.useWatch('category', form)
  const timer = useRef<number>(0)

  const load = useCallback(async () => {
    const { data } = await api.get<Task[]>('/tasks')
    setTasks(data)
    if (data.some((t) => ['pending', 'running'].includes(t.status))) {
      timer.current = window.setTimeout(load, 2000)
    }
  }, [])

  useEffect(() => {
    load()
    api.get<Doc[]>('/documents').then((r) => setDocs(r.data.filter((d) => d.parse_status === 'done')))
    api.get('/categories').then((r) => { setCategories(r.data.categories); setSubMap(r.data.subcategories) })
    return () => clearTimeout(timer.current)
  }, [load])

  useEffect(() => {
    const docId = params.get('doc')
    if (docId) {
      form.setFieldValue('document_id', Number(docId))
      setOpen(true)
      setParams({}, { replace: true })
    }
  }, [params, form, setParams])

  const submit = async () => {
    const v = await form.validateFields()
    const type_counts: Record<string, number> = {}
    for (const t of Object.keys(Q_TYPE_LABELS)) {
      if (v[t] > 0) type_counts[t] = v[t]
    }
    if (!Object.keys(type_counts).length) { message.warning('请至少填写一种题型的数量'); return }
    const sub = Array.isArray(v.subcategory) ? (v.subcategory[0] ?? '') : (v.subcategory ?? '')
    await api.post('/tasks', {
      document_id: v.document_id, type_counts, difficulty: v.difficulty,
      category: v.category ?? '', subcategory: sub,
    })
    message.success('任务已提交，AI 正在出题')
    setOpen(false); form.resetFields(); load()
  }

  return (
    <div>
      <Typography.Title level={3}>生成任务</Typography.Title>
      <Button type="primary" onClick={() => setOpen(true)} style={{ marginBottom: 16 }}>新建生成任务</Button>
      <Table<Task>
        rowKey="id" dataSource={tasks} size="middle"
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          {
            title: '资料', dataIndex: 'document_id', width: 220,
            render: (id: number) => docs.find((d) => d.id === id)?.filename ?? `资料#${id}`,
          },
          {
            title: '题型配置',
            render: (_, t) => Object.entries(t.config.type_counts)
              .map(([k, n]) => `${Q_TYPE_LABELS[k] ?? k}×${n}`).join('、'),
          },
          { title: '模型', dataIndex: 'model_name', width: 150 },
          {
            title: '状态', dataIndex: 'status', width: 100,
            render: (s: string, t) => <Tag color={STATUS_TAG[s]?.color} title={t.error_msg ?? ''}>{STATUS_TAG[s]?.text ?? s}</Tag>,
          },
          { title: '生成题数', dataIndex: 'question_count', width: 90 },
          {
            title: '操作', width: 140,
            render: (_, t) => (
              <>
                {t.status === 'done' && <Link to="/review">去审核</Link>}{' '}
                {t.error_msg && (
                  <Button size="small" danger type="text" icon={<ExclamationCircleOutlined />}
                    onClick={() => Modal.error({
                      title: `任务 #${t.id} 错误详情`, width: 680,
                      content: <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto' }}>{t.error_msg}</pre>,
                    })}>
                    查看错误
                  </Button>
                )}
              </>
            ),
          },
        ]}
      />
      <Modal open={open} title="新建生成任务" onOk={submit} onCancel={() => setOpen(false)} okText="开始生成">
        <Form form={form} layout="vertical" initialValues={{ difficulty: 'medium' }}>
          <Form.Item name="document_id" label="选择资料" rules={[{ required: true, message: '请选择资料' }]}>
            <Select options={docs.map((d) => ({ value: d.id, label: d.filename }))} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item label="题型与数量">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
              {Object.entries(Q_TYPE_LABELS).map(([k, label]) => (
                <Form.Item key={k} name={k} noStyle>
                  <InputNumber min={0} max={50} placeholder="0" addonBefore={label} style={{ width: '100%' }} />
                </Form.Item>
              ))}
            </div>
          </Form.Item>
          <Form.Item name="difficulty" label="难度">
            <Select options={[
              { value: 'easy', label: '简单' },
              { value: 'medium', label: '中等' },
              { value: 'hard', label: '困难' },
            ]} />
          </Form.Item>
          <div style={{ display: 'flex', gap: 8 }}>
            <Form.Item name="category" label="大类" style={{ flex: 1 }}
              tooltip="生成的题目会继承该大类，审核时仍可逐题修改">
              <Select allowClear placeholder="可选" options={categories.map((c) => ({ value: c, label: c }))} />
            </Form.Item>
            <Form.Item name="subcategory" label="小类（可空）" style={{ flex: 1 }}>
              <Select allowClear showSearch placeholder="可填可选" mode="tags" maxCount={1}
                options={(subMap[category] ?? []).map((s) => ({ value: s, label: s }))} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  )
}
