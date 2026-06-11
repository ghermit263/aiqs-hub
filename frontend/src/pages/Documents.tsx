import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button, Drawer, List, Popconfirm, Table, Tag, Typography, Upload, message,
} from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api, type Doc } from '../api'

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '等待解析' },
  parsing: { color: 'processing', text: '解析中' },
  done: { color: 'success', text: '解析完成' },
  failed: { color: 'error', text: '解析失败' },
}

interface Chunk { id: number; chunk_index: number; content: string; source_locator: string; char_count: number }

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [loading, setLoading] = useState(false)
  const [chunks, setChunks] = useState<Chunk[] | null>(null)
  const [chunkDoc, setChunkDoc] = useState<Doc | null>(null)
  const navigate = useNavigate()
  const timer = useRef<number>(0)
  const canGenerate = localStorage.getItem('role') !== 'uploader'

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get<Doc[]>('/documents')
      setDocs(data)
      // 有解析中的文件则轮询
      if (data.some((d) => ['pending', 'parsing'].includes(d.parse_status))) {
        timer.current = window.setTimeout(load, 1500)
      }
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load(); return () => clearTimeout(timer.current) }, [load])

  const showChunks = async (doc: Doc) => {
    const { data } = await api.get(`/documents/${doc.id}/chunks`)
    setChunkDoc(doc); setChunks(data)
  }

  return (
    <div>
      <Typography.Title level={3}>资料管理</Typography.Title>
      <Upload.Dragger
        multiple
        showUploadList={false}
        customRequest={async ({ file, onSuccess, onError }) => {
          const form = new FormData()
          form.append('file', file as File)
          try {
            await api.post('/documents', form)
            message.success('上传成功，开始解析')
            onSuccess?.(null); load()
          } catch (e) { onError?.(e as Error) }
        }}
        style={{ marginBottom: 16 }}
      >
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">点击或拖拽上传培训资料</p>
        <p className="ant-upload-hint">支持 PDF / Word(.docx) / PPT(.pptx) / Excel(.xlsx) / 文本(.txt) / 图片(.jpg .png，本地OCR识别)</p>
      </Upload.Dragger>
      <Table<Doc>
        rowKey="id" dataSource={docs} loading={loading} size="middle"
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '文件名', dataIndex: 'filename' },
          { title: '类型', dataIndex: 'file_type', width: 80 },
          {
            title: '解析状态', dataIndex: 'parse_status', width: 110,
            render: (s: string, r) => (
              <Tag color={STATUS_TAG[s]?.color} title={r.parse_error ?? ''}>{STATUS_TAG[s]?.text ?? s}</Tag>
            ),
          },
          { title: '切片数', dataIndex: 'chunk_count', width: 80 },
          { title: '上传时间', dataIndex: 'created_at', width: 170, render: (t: string) => t?.replace('T', ' ').slice(0, 19) },
          {
            title: '操作', width: 280,
            render: (_, doc) => (
              <>
                <Button size="small" disabled={doc.parse_status !== 'done'} onClick={() => showChunks(doc)}>查看切片</Button>{' '}
                {canGenerate && (
                  <><Button size="small" type="primary" disabled={doc.parse_status !== 'done'}
                    onClick={() => navigate(`/tasks?doc=${doc.id}`)}>生成题目</Button>{' '}</>
                )}
                <Popconfirm title="确定删除该资料？" onConfirm={async () => { await api.delete(`/documents/${doc.id}`); message.success('已删除'); load() }}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </>
            ),
          },
        ]}
      />
      <Drawer open={!!chunks} width={640} title={`切片预览 — ${chunkDoc?.filename ?? ''}`}
        onClose={() => setChunks(null)}>
        <List
          dataSource={chunks ?? []}
          renderItem={(c) => (
            <List.Item>
              <List.Item.Meta
                title={<Tag color="blue">{c.source_locator}</Tag>}
                description={<pre className="ths-code">{c.content}</pre>}
              />
            </List.Item>
          )}
        />
      </Drawer>
    </div>
  )
}
