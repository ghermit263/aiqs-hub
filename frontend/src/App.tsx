import { useEffect, useState } from 'react'
import { Layout, Menu, Button, Typography, Modal, Form, Input, Space, Segmented, message } from 'antd'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  DashboardOutlined, FileTextOutlined, ThunderboltOutlined, FileDoneOutlined,
  AuditOutlined, DatabaseOutlined, SettingOutlined, LogoutOutlined, KeyOutlined, SkinOutlined,
} from '@ant-design/icons'
import { api } from './api'
import { useSkin } from './ThemeProvider'
import { SKINS, SKIN_ORDER } from './theme'

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const { skin, setSkin } = useSkin()
  const [pwdOpen, setPwdOpen] = useState(false)
  const [pwdForm] = Form.useForm()
  const role = localStorage.getItem('role') ?? 'uploader'
  const username = localStorage.getItem('username') ?? ''
  const cur = SKINS[skin]

  useEffect(() => {
    if (!localStorage.getItem('token')) navigate('/login')
  }, [navigate])

  const items = [
    { key: '/', icon: <DashboardOutlined />, label: <Link to="/">工作台</Link> },
    { key: '/documents', icon: <FileTextOutlined />, label: <Link to="/documents">资料管理</Link> },
    ...(role !== 'uploader' ? [
      { key: '/tasks', icon: <ThunderboltOutlined />, label: <Link to="/tasks">生成任务</Link> },
      { key: '/review', icon: <AuditOutlined />, label: <Link to="/review">审核工作台</Link> },
      { key: '/papers', icon: <FileDoneOutlined />, label: <Link to="/papers">试卷组卷</Link> },
    ] : []),
    { key: '/bank', icon: <DatabaseOutlined />, label: <Link to="/bank">标准题库</Link> },
    ...(role === 'admin' ? [
      { key: '/settings', icon: <SettingOutlined />, label: <Link to="/settings">系统设置</Link> },
    ] : []),
  ]

  const changePassword = async () => {
    const v = await pwdForm.validateFields()
    if (v.new_password !== v.confirm) { message.error('两次输入的新密码不一致'); return }
    await api.post('/auth/change-password', {
      old_password: v.old_password, new_password: v.new_password,
    })
    message.success('密码已修改，请重新登录')
    setPwdOpen(false)
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider theme={cur.menuTheme} width={210}
        style={{ background: 'var(--ths-sider-bg)' }}>
        <Typography.Title level={4} style={{ color: 'var(--ths-sider-title)', textAlign: 'center', margin: '20px 0' }}>
          智能题源中心
        </Typography.Title>
        <Menu theme={cur.menuTheme} mode="inline" selectedKeys={[location.pathname]} items={items}
          style={{ background: 'transparent', borderInlineEnd: 'none' }} />
        <div style={{ position: 'absolute', bottom: 16, width: '100%', textAlign: 'center' }}>
          <Space direction="vertical" size={6}>
            <Space size={4}>
              <SkinOutlined style={{ color: 'var(--ths-sider-title)' }} />
              <Segmented size="small" value={skin} onChange={(v) => setSkin(v as typeof skin)}
                options={SKIN_ORDER.map((k) => ({ value: k, label: SKINS[k].label }))} />
            </Space>
            <Typography.Text style={{ color: cur.menuTheme === 'dark' ? '#cbb' : 'var(--ths-muted)', fontSize: 12 }}>
              {username}（{{ admin: '管理员', reviewer: '审核人', uploader: '上传人' }[role]}）
            </Typography.Text>
            <Space size={2}>
              <Button type="text" size="small" style={{ color: 'var(--ths-sider-title)' }} icon={<KeyOutlined />}
                onClick={() => setPwdOpen(true)}>改密</Button>
              <Button type="text" size="small" style={{ color: 'var(--ths-sider-title)' }} icon={<LogoutOutlined />}
                onClick={() => { localStorage.removeItem('token'); navigate('/login') }}>退出</Button>
            </Space>
          </Space>
        </div>
      </Layout.Sider>
      <Layout.Content style={{ padding: 24, overflow: 'auto' }}>
        <Outlet />
      </Layout.Content>
      <Modal open={pwdOpen} title="修改密码" onOk={changePassword} onCancel={() => setPwdOpen(false)} okText="确认修改">
        <Form form={pwdForm} layout="vertical">
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6, message: '新密码至少 6 位' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirm" label="确认新密码" rules={[{ required: true, message: '请再次输入新密码' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}
