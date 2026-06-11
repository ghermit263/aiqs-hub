import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { api } from '../api'

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

export default function Settings() {
  const [form] = Form.useForm()
  const [provider, setProvider] = useState('mock')
  const [testing, setTesting] = useState(false)
  const isAdmin = localStorage.getItem('role') === 'admin'

  useEffect(() => {
    api.get('/settings/models').then((r) => {
      form.setFieldsValue(r.data)
      setProvider(r.data.llm_provider)
    })
  }, [form])

  const save = async () => {
    const v = await form.validateFields()
    await api.put('/settings/models', v)
    message.success('模型配置已保存')
  }

  const testConnection = async () => {
    setTesting(true)
    try {
      const { data } = await api.post('/settings/models/test')
      if (data.ok) {
        Modal.success({
          title: '连接正常',
          content: `${data.provider}:${data.model} 响应 ${data.latency_ms}ms，回复：${data.reply}`,
        })
      } else {
        Modal.error({
          title: '连接失败',
          width: 640,
          content: <pre style={{ whiteSpace: 'pre-wrap' }}>{data.error}</pre>,
        })
      }
    } finally { setTesting(false) }
  }

  return (
    <div>
      <Typography.Title level={3}>系统设置</Typography.Title>
      <Card title="模型配置（model_gateway）" style={{ maxWidth: 880 }}>
        {!isAdmin && <Alert type="warning" message="只有管理员可以修改模型配置" style={{ marginBottom: 12 }} />}
        <Form form={form} layout="vertical" disabled={!isAdmin} style={{ maxWidth: 600 }}>
          <Form.Item name="llm_provider" label="模型供应商" rules={[{ required: true }]}>
            <Select options={PROVIDER_OPTIONS} onChange={setProvider} />
          </Form.Item>
          {provider !== 'mock' && (
            <>
              {provider === 'openai_compat' && (
                <Form.Item label="常用地址速填">
                  {Object.entries(PRESETS).map(([name, url]) => (
                    <Button key={name} size="small" style={{ marginRight: 8 }}
                      onClick={() => form.setFieldValue('llm_base_url', url)}>{name}</Button>
                  ))}
                </Form.Item>
              )}
              <Form.Item name="llm_base_url" label="API 地址 (base_url)"
                rules={provider === 'openai_compat' ? [{ required: true, message: '请填写 API 地址' }] : []}>
                <Input placeholder="如 https://api.deepseek.com/v1 或内网 http://10.x.x.x:8000/v1" />
              </Form.Item>
              <Form.Item name="llm_api_key" label="API Key" extra="留空表示不修改已保存的密钥">
                <Input.Password placeholder="sk-..." />
              </Form.Item>
              <Form.Item name="llm_model" label="模型名称" rules={[{ required: true, message: '请填写模型名' }]}>
                <Input placeholder="如 deepseek-chat / qwen-plus / claude-sonnet-4-6" />
              </Form.Item>
            </>
          )}
          <Form.Item name="intranet_only" label="内网模式" valuePropName="checked"
            extra="开启后仅允许调用内网地址的模型服务，涉密资料（绩效、薪资等）出题时务必开启">
            <Switch />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={save} disabled={!isAdmin}>保存配置</Button>
            <Button onClick={testConnection} loading={testing} disabled={!isAdmin}>测试连接</Button>
            <Typography.Text type="secondary">先保存再测试；失败时会显示服务商返回的完整错误</Typography.Text>
          </Space>
        </Form>
      </Card>
      {isAdmin && <LogPanel />}
      {isAdmin && <UserManagement />}
    </div>
  )
}
