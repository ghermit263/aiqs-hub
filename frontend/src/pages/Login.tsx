import { useState } from 'react'
import { Button, Card, Form, Input, Modal, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Login() {
  const navigate = useNavigate()
  const [regOpen, setRegOpen] = useState(false)
  const [regForm] = Form.useForm()

  const onFinish = async (values: { username: string; password: string }) => {
    const { data } = await api.post('/auth/login', values)
    localStorage.setItem('token', data.token)
    localStorage.setItem('role', data.role)
    localStorage.setItem('username', data.username)
    message.success(`欢迎，${data.display_name || data.username}`)
    navigate('/')
  }

  const onRegister = async () => {
    const v = await regForm.validateFields()
    if (v.password !== v.confirm) { message.error('两次输入的密码不一致'); return }
    const { data } = await api.post('/auth/register', {
      username: v.username, password: v.password, display_name: v.display_name ?? '',
    })
    message.success(data.message)
    setRegOpen(false)
    regForm.resetFields()
  }

  return (
    <div className="ths-login">
      <Card style={{ width: 380 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>智能题源中心</Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          AI 生成 · 人工审核 · 一键导出组卷模板
        </Typography.Paragraph>
        <Form onFinish={onFinish}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input placeholder="用户名" size="large" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="密码" size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large">登录</Button>
        </Form>
        <div style={{ textAlign: 'center', marginTop: 12 }}>
          <Button type="link" onClick={() => setRegOpen(true)}>没有账号？注册（需管理员审批）</Button>
        </div>
      </Card>
      <Modal open={regOpen} title="注册新账号" onOk={onRegister} onCancel={() => setRegOpen(false)} okText="提交注册">
        <Form form={regForm} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[
            { required: true, min: 2, max: 32, message: '用户名 2-32 个字符' }]}>
            <Input placeholder="建议用工号或姓名拼音" />
          </Form.Item>
          <Form.Item name="display_name" label="姓名">
            <Input placeholder="显示用，可选" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[
            { required: true, min: 6, message: '密码至少 6 位' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirm" label="确认密码" rules={[{ required: true, message: '请再次输入密码' }]}>
            <Input.Password />
          </Form.Item>
          <Typography.Text type="secondary">注册后账号为“待审批”状态，管理员通过后即可登录，默认角色为资料上传人。</Typography.Text>
        </Form>
      </Modal>
    </div>
  )
}
