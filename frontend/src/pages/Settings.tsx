import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag,
  Typography, Upload, message,
} from 'antd'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons'
import { api } from '../api'

const PROVIDER_LABEL: Record<string, string> = {
  mock: 'Mock', openai_compat: 'OpenAI兼容', claude: 'Claude',
}

const PROVIDER_OPTIONS = [
  { value: 'mock', label: 'Mock（演示模式，不调用真实模型）' },
  { value: 'openai_compat', label: 'OpenAI 兼容（DeepSeek / 通义 / 豆包 / 内网vLLM 等）' },
  { value: 'claude', label: 'Anthropic Claude' },
]

const PRESETS: Record<string, string> = {
  DeepSeek: 'https://api.deepseek.com/v1',
  通义千问: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  豆包: 'https://ark.cn-beijing.volces.com/api/v3',
  OpenAI: 'https://api.openai.com/v1',
}

const ROLE_OPTIONS = [
  { value: 'uploader', label: '上传人' },
  { value: 'reviewer', label: '审核人' },
  { value: 'admin', label: '管理员' },
]

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  pending: { color: 'warning', text: '待审批' },
  active: { color: 'success', text: '正常' },
  disabled: { color: 'default', text: '已停用' },
}

interface UserRow {
  id: number; username: string; display_name: string; role: string; status: string; created_at: string
}

function UserManagement() {
  const [users, setUsers] = useState<UserRow[]>([])
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm] = Form.useForm()
  const myName = localStorage.getItem('username')

  const load = useCallback(() => { api.get('/users').then((r) => setUsers(r.data)) }, [])
  useEffect(() => { load() }, [load])

  const update = async (id: number, body: Record<string, string>) => {
    await api.put(`/users/${id}`, body)
    message.success('已更新')
    load()
  }

  const resetPassword = (u: UserRow) => {
    let pwd = ''
    Modal.confirm({
      title: `重置 ${u.display_name || u.username} 的密码`,
      content: <Input.Password placeholder="输入新密码（至少6位）" onChange={(e) => { pwd = e.target.value }} />,
      onOk: async () => {
        if (pwd.length < 6) { message.error('密码至少 6 位'); throw new Error() }
        await update(u.id, { new_password: pwd })
      },
    })
  }

  const createUser = async () => {
    const v = await createForm.validateFields()
    await api.post('/users', v)
    message.success('账号已创建（直接可用）')
    setCreateOpen(false)
    createForm.resetFields()
    load()
  }

  return (
    <Card title="用户管理" style={{ maxWidth: 880, marginTop: 24 }}
      extra={<Button type="primary" size="small" onClick={() => setCreateOpen(true)}>手工建号</Button>}>
      <Table<UserRow>
        rowKey="id" dataSource={users} size="small" pagination={false}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 50 },
          { title: '用户名', dataIndex: 'username' },
          { title: '姓名', dataIndex: 'display_name' },
          {
            title: '角色', dataIndex: 'role', width: 120,
            render: (role: string, u) => (
              <Select size="small" value={role} options={ROLE_OPTIONS} style={{ width: 100 }}
                disabled={u.username === myName}
                onChange={(v) => update(u.id, { role: v })} />
            ),
          },
          {
            title: '状态', dataIndex: 'status', width: 90,
            render: (s: string) => <Tag color={STATUS_TAG[s]?.color}>{STATUS_TAG[s]?.text}</Tag>,
          },
          {
            title: '操作', width: 240,
            render: (_, u) => (
              <>
                {u.status === 'pending' && (
                  <Button size="small" type="primary" onClick={() => update(u.id, { status: 'active' })}>
                    审批通过
                  </Button>
                )}{' '}
                {u.status === 'active' && u.username !== myName && (
                  <Button size="small" danger onClick={() => update(u.id, { status: 'disabled' })}>停用</Button>
                )}{' '}
                {u.status === 'disabled' && (
                  <Button size="small" onClick={() => update(u.id, { status: 'active' })}>启用</Button>
                )}{' '}
                <Button size="small" onClick={() => resetPassword(u)}>重置密码</Button>
              </>
            ),
          },
        ]}
      />
      <Modal open={createOpen} title="手工创建账号" onOk={createUser} onCancel={() => setCreateOpen(false)}>
        <Form form={createForm} layout="vertical" initialValues={{ role: 'uploader' }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, min: 2 }]}><Input /></Form.Item>
          <Form.Item name="display_name" label="姓名"><Input /></Form.Item>
          <Form.Item name="password" label="初始密码" rules={[{ required: true, min: 6 }]}><Input.Password /></Form.Item>
          <Form.Item name="role" label="角色"><Select options={ROLE_OPTIONS} /></Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

interface LlmLog {
  id: number; task_id: number | null; provider: string; model: string
  latency_ms: number; success: boolean; error_msg: string | null; created_at: string
  prompt_tokens: number; completion_tokens: number
}

function LogPanel() {
  const [llmLogs, setLlmLogs] = useState<LlmLog[]>([])
  const [appLog, setAppLog] = useState<string[]>([])
  const [showApp, setShowApp] = useState(false)

  const load = useCallback(() => {
    api.get('/settings/llm-logs').then((r) => setLlmLogs(r.data))
  }, [])
  useEffect(() => { load() }, [load])

  const loadAppLog = async () => {
    const { data } = await api.get('/settings/app-log')
    setAppLog(data.lines)
    setShowApp(true)
  }

  return (
    <Card title="调用与运行日志" style={{ maxWidth: 880, marginTop: 24 }}
      extra={<Space>
        <Button size="small" onClick={load}>刷新</Button>
        <Button size="small" onClick={loadAppLog}>查看运行日志</Button>
      </Space>}>
      <Table<LlmLog>
        rowKey="id" dataSource={llmLogs} size="small" pagination={{ pageSize: 10 }}
        columns={[
          { title: '时间', dataIndex: 'created_at', width: 150, render: (t: string) => t?.replace('T', ' ').slice(5, 19) },
          { title: '任务', dataIndex: 'task_id', width: 60, render: (t) => t ?? '-' },
          { title: '模型', render: (_, r) => `${r.provider}:${r.model}`, width: 200 },
          { title: '耗时', dataIndex: 'latency_ms', width: 80, render: (v: number) => `${v}ms` },
          {
            title: '结果', dataIndex: 'success', width: 70,
            render: (s: boolean) => <Tag color={s ? 'success' : 'error'}>{s ? '成功' : '失败'}</Tag>,
          },
          {
            title: '错误信息', dataIndex: 'error_msg', ellipsis: true,
            render: (e: string | null) => e
              ? <a onClick={() => Modal.error({ title: '错误详情', width: 640, content: <pre style={{ whiteSpace: 'pre-wrap' }}>{e}</pre> })}>{e}</a>
              : '-',
          },
        ]}
      />
      {showApp && (
        <pre className="ths-code" style={{ maxHeight: 300, marginTop: 12 }}>
          {appLog.join('\n') || '（暂无日志）'}
        </pre>
      )}
    </Card>
  )
}

interface Profile {
  name: string; provider: string; base_url: string; model: string
  api_key: string; has_key?: boolean
}

function ModelConfig({ isAdmin }: { isAdmin: boolean }) {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [active, setActive] = useState<string>('')
  const [intranet, setIntranet] = useState(false)
  const [testing, setTesting] = useState(false)
  const [edit, setEdit] = useState<{ profile: Profile; isNew: boolean } | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(() => {
    api.get('/settings/models').then((r) => {
      setProfiles(r.data.profiles)
      setActive(r.data.active)
      setIntranet(r.data.intranet_only)
    })
  }, [])
  useEffect(() => { load() }, [load])

  // 统一保存整张配置表（active 可覆盖）
  const persist = async (next: Profile[], nextActive = active, nextIntranet = intranet) => {
    await api.put('/settings/models', {
      profiles: next.map((p) => ({
        name: p.name, provider: p.provider, base_url: p.base_url,
        model: p.model, api_key: p.api_key,  // 掩码/空 → 后端保留旧密钥
      })),
      active: nextActive, intranet_only: nextIntranet,
    })
    load()
  }

  // 下拉切换当前启用模型（即时生效）
  const switchActive = async (name: string) => {
    setActive(name)
    await api.put('/settings/models/active', { active: name })
    message.success(`已切换到「${name}」`)
  }

  const openAdd = () => {
    form.resetFields()
    form.setFieldsValue({ provider: 'openai_compat' })
    setEdit({ profile: { name: '', provider: 'openai_compat', base_url: '', model: '', api_key: '' }, isNew: true })
  }
  const openEdit = (p: Profile) => {
    form.setFieldsValue({ name: p.name, provider: p.provider, base_url: p.base_url, model: p.model, api_key: '' })
    setEdit({ profile: p, isNew: false })
  }

  const submitEdit = async () => {
    const v = await form.validateFields()
    const np: Profile = {
      name: v.name.trim(), provider: v.provider, base_url: (v.base_url || '').trim(),
      model: (v.model || '').trim(),
      api_key: v.api_key ? v.api_key : (edit!.isNew ? '' : '****'),  // 留空：新增=空，编辑=保留
    }
    let next: Profile[]
    if (edit!.isNew) {
      if (profiles.some((p) => p.name === np.name)) { message.error('名称已存在'); return }
      next = [...profiles, np]
    } else {
      next = profiles.map((p) => (p.name === edit!.profile.name ? np : p))
    }
    await persist(next, edit!.isNew && profiles.length === 0 ? np.name : active)
    setEdit(null)
    message.success('已保存')
  }

  const remove = async (name: string) => {
    if (profiles.length <= 1) { message.warning('至少保留一个模型配置'); return }
    const next = profiles.filter((p) => p.name !== name)
    await persist(next, name === active ? next[0].name : active)
    message.success('已删除')
  }

  const setIntranetMode = async (v: boolean) => { setIntranet(v); await persist(profiles, active, v) }

  const testConnection = async () => {
    setTesting(true)
    try {
      const { data } = await api.post('/settings/models/test')
      if (data.ok) {
        Modal.success({ title: '连接正常', content: `${data.provider}:${data.model} 响应 ${data.latency_ms}ms，回复：${data.reply}` })
      } else {
        Modal.error({ title: '连接失败', width: 640, content: <pre style={{ whiteSpace: 'pre-wrap' }}>{data.error}</pre> })
      }
    } finally { setTesting(false) }
  }

  const editProvider = Form.useWatch('provider', form)

  return (
    <Card title="模型配置（model_gateway · 多模型多API）" style={{ maxWidth: 880 }}>
      {!isAdmin && <Alert type="warning" message="只有管理员可以修改模型配置" style={{ marginBottom: 12 }} />}
      <Space style={{ marginBottom: 12 }} wrap>
        <span>当前启用模型：</span>
        <Select value={active} style={{ width: 220 }} disabled={!isAdmin} onChange={switchActive}
          options={profiles.map((p) => ({ value: p.name, label: `${p.name}（${PROVIDER_LABEL[p.provider] ?? p.provider}）` }))} />
        <Button onClick={testConnection} loading={testing} disabled={!isAdmin}>测试连接</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={openAdd} disabled={!isAdmin}>新增模型</Button>
      </Space>
      <Table<Profile>
        rowKey="name" dataSource={profiles} size="small" pagination={false}
        columns={[
          { title: '名称', dataIndex: 'name', render: (n: string) => n === active ? <b>{n}（启用中）</b> : n },
          { title: '供应商', dataIndex: 'provider', width: 110, render: (p: string) => PROVIDER_LABEL[p] ?? p },
          { title: '模型', dataIndex: 'model', width: 160, render: (m: string) => m || '—' },
          { title: '密钥', dataIndex: 'has_key', width: 70, render: (h: boolean) => h ? <Tag color="green">已存</Tag> : <Tag>无</Tag> },
          ...(isAdmin ? [{
            title: '操作', width: 130,
            render: (_: unknown, p: Profile) => (
              <Space size={4}>
                <Button size="small" onClick={() => openEdit(p)}>编辑</Button>
                <Popconfirm title={`删除「${p.name}」？`} onConfirm={() => remove(p.name)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          }] : []),
        ]}
      />
      <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Switch checked={intranet} disabled={!isAdmin} onChange={setIntranetMode} />
        <span>内网模式</span>
        <Typography.Text type="secondary">开启后仅允许内网地址的模型服务，处理敏感资料时建议开启</Typography.Text>
      </div>

      <Modal open={!!edit} title={edit?.isNew ? '新增模型配置' : '编辑模型配置'}
        onOk={submitEdit} onCancel={() => setEdit(null)} okText="保存">
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="配置名称" rules={[{ required: true, message: '给这个模型起个名，如 DeepSeek-正式' }]}>
            <Input placeholder="如 DeepSeek / 通义 / 内网vLLM" disabled={!edit?.isNew} />
          </Form.Item>
          <Form.Item name="provider" label="供应商" rules={[{ required: true }]}>
            <Select options={PROVIDER_OPTIONS} />
          </Form.Item>
          {editProvider !== 'mock' && (
            <>
              {editProvider === 'openai_compat' && (
                <Form.Item label="常用地址速填">
                  {Object.entries(PRESETS).map(([n, url]) => (
                    <Button key={n} size="small" style={{ marginRight: 8 }}
                      onClick={() => form.setFieldValue('base_url', url)}>{n}</Button>
                  ))}
                </Form.Item>
              )}
              <Form.Item name="base_url" label="API 地址 (base_url)"
                rules={editProvider === 'openai_compat' ? [{ required: true, message: '请填写 API 地址' }] : []}>
                <Input placeholder="如 https://api.deepseek.com/v1 或内网 http://10.x.x.x:8000/v1" />
              </Form.Item>
              <Form.Item name="api_key" label="API Key" extra="留空表示不修改已保存的密钥">
                <Input.Password placeholder="sk-..." />
              </Form.Item>
              <Form.Item name="model" label="模型名称" rules={[{ required: true, message: '请填写模型名' }]}>
                <Input placeholder="如 deepseek-chat / qwen-plus / claude-sonnet-4-6" />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </Card>
  )
}

function GuidanceCard({ isAdmin }: { isAdmin: boolean }) {
  const [text, setText] = useState('')
  useEffect(() => { api.get('/settings/guidance').then((r) => setText(r.data.guidance)) }, [])
  const save = async () => { await api.put('/settings/guidance', { guidance: text }); message.success('已保存') }
  return (
    <Card title="自定义命题指引（非通用规则）" style={{ maxWidth: 880, marginTop: 24 }}
      extra={isAdmin && (
        <Upload accept=".txt,.md" showUploadList={false}
          beforeUpload={(file) => {
            const reader = new FileReader()
            reader.onload = () => setText(String(reader.result || ''))
            reader.readAsText(file, 'utf-8')
            return false
          }}>
          <Button size="small" icon={<UploadOutlined />}>导入 txt</Button>
        </Upload>
      )}>
      <Typography.Paragraph type="secondary">
        通用干扰策略已内置进系统提示词。这里只填**本单位专属**的补充规则（如党建专项口径、特定业务术语），
        出题时会追加到提示词后，并仍以所给原文为准。
      </Typography.Paragraph>
      <Input.TextArea value={text} onChange={(e) => setText(e.target.value)} disabled={!isAdmin}
        autoSize={{ minRows: 5, maxRows: 16 }}
        placeholder="例：涉及党章表述时，干扰项只能基于党章原文相近字眼的差异（如“党委/党组”“警告/严重警告”），不得自拟。" />
      <Button type="primary" style={{ marginTop: 12 }} onClick={save} disabled={!isAdmin}>保存指引</Button>
    </Card>
  )
}

export default function Settings() {
  const isAdmin = localStorage.getItem('role') === 'admin'
  return (
    <div>
      <Typography.Title level={3}>系统设置</Typography.Title>
      <ModelConfig isAdmin={isAdmin} />
      {isAdmin && <GuidanceCard isAdmin={isAdmin} />}
      {isAdmin && <LogPanel />}
      {isAdmin && <UserManagement />}
    </div>
  )
}
