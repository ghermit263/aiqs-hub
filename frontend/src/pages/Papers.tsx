import { useCallback, useEffect, useState } from 'react'
import {
  Button, Card, Divider, Drawer, Empty, Input, InputNumber, List, Modal, Radio, Select,
  Space, Table, Tabs, Tag, Typography, message,
} from 'antd'
import { DeleteOutlined, DownloadOutlined, EyeOutlined, PlusOutlined, SwapOutlined } from '@ant-design/icons'
import { DEFAULT_CATEGORIES, Q_TYPE_LABELS, api } from '../api'

interface Criterion { q_type: string; category: string; difficulty: string; count: number; score: number }
interface DraftQ {
  id: number; q_type: string; stem: string; options: { key: string; text: string }[] | null
  answer: string; difficulty: string; category: string; subcategory: string; score: number
}
interface DraftSection { q_type: string; label: string; questions: DraftQ[] }
// 预览：每个卷别是排版后的 sections（含题号 no / 乱序选项 / 答案）
interface PreviewQ { no: number; stem: string; options: { key: string; text: string }[] | null; answer: string; score: number }
interface PreviewSection { q_type: string; label: string; questions: PreviewQ[]; per_score: number | null; total: number }
type PreviewData = Record<string, PreviewSection[]>
interface PaperRow {
  id: number; title: string; venue: string; question_count: number; total_score: number
  category_distribution: Record<string, number>; versions: string[]; files: string[]
  created_at: string; download_url: string
}

const DIFF_OPTIONS = [
  { value: 'any', label: '不限' }, { value: 'easy', label: '简单' },
  { value: 'medium', label: '中等' }, { value: 'hard', label: '困难' },
]

export default function Papers() {
  const [title, setTitle] = useState('')
  const [venue, setVenue] = useState('')
  const [criteria, setCriteria] = useState<Criterion[]>([
    { q_type: 'single', category: 'any', difficulty: 'any', count: 10, score: 1 },
  ])
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES)
  const [stock, setStock] = useState<Record<string, Record<string, number>>>({})
  const [papers, setPapers] = useState<PaperRow[]>([])
  const [sections, setSections] = useState<DraftSection[] | null>(null)  // 草稿
  const [versions, setVersions] = useState<string[]>(['A', 'B'])  // 卷别选择
  const [drafting, setDrafting] = useState(false)
  const [finalizing, setFinalizing] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [swapTarget, setSwapTarget] = useState<{ secIdx: number; qIdx: number } | null>(null)
  const [alts, setAlts] = useState<DraftQ[]>([])
  const [preview, setPreview] = useState<{ title: string; data: PreviewData } | null>(null)

  const load = useCallback(() => {
    api.get('/papers').then((r) => setPapers(r.data))
    api.get('/papers/stock').then((r) => setStock(r.data))
    api.get('/categories').then((r) => setCategories(r.data.categories))
  }, [])
  useEffect(() => { load() }, [load])

  const totalScore = criteria.reduce((s, c) => s + c.count * c.score, 0)
  const totalCount = criteria.reduce((s, c) => s + c.count, 0)
  const setRow = (i: number, patch: Partial<Criterion>) =>
    setCriteria(criteria.map((c, j) => (j === i ? { ...c, ...patch } : c)))

  const makeDraft = async () => {
    if (!title.trim()) { message.warning('请填写试卷标题'); return }
    setDrafting(true)
    try {
      const { data } = await api.post('/papers/draft', { criteria })
      setSections(data.sections)
      message.success(`已自动组卷 ${data.total_questions} 题，可在下方微调`)
    } finally { setDrafting(false) }
  }

  // 当前草稿用到的全部题目ID（换题时排除）
  const usedIds = () => (sections ?? []).flatMap((s) => s.questions.map((q) => q.id))

  const openSwap = async (secIdx: number, qIdx: number) => {
    const q = sections![secIdx].questions[qIdx]
    setSwapTarget({ secIdx, qIdx })
    const { data } = await api.get('/papers/alternatives', {
      params: { q_type: q.q_type, category: q.category || 'any', difficulty: 'any',
                exclude: usedIds().join(',') },
    })
    setAlts(data)
  }

  const doSwap = (alt: DraftQ) => {
    const { secIdx, qIdx } = swapTarget!
    const orig = sections![secIdx].questions[qIdx]
    const next = sections!.map((s, i) => i !== secIdx ? s : {
      ...s, questions: s.questions.map((q, j) => j !== qIdx ? q : { ...alt, score: orig.score }),
    })
    setSections(next)
    setSwapTarget(null)
    message.success(`已换为题 #${alt.id}`)
  }

  const removeQ = (secIdx: number, qIdx: number) => {
    const next = sections!.map((s, i) => i !== secIdx ? s
      : { ...s, questions: s.questions.filter((_, j) => j !== qIdx) })
      .filter((s) => s.questions.length > 0)
    setSections(next)
  }

  const draftCatSummary = () => {
    const m: Record<string, number> = {}
    for (const s of sections ?? []) for (const q of s.questions) {
      const k = q.category || '未分类'
      m[k] = (m[k] ?? 0) + 1
    }
    return m
  }

  const sectionsPayload = () => sections!.map((s) => ({
    q_type: s.q_type,
    score: s.questions[0]?.score ?? 1,
    question_ids: s.questions.map((q) => q.id),
  }))

  const doPreview = async () => {
    if (!sections?.length) return
    setPreviewing(true)
    try {
      const { data } = await api.post('/papers/preview', {
        title: title.trim() || '试卷预览', sections: sectionsPayload(), versions,
      })
      setPreview({ title: title.trim() || '试卷预览', data: data.preview })
    } finally { setPreviewing(false) }
  }

  const finalize = async () => {
    if (!sections?.length) return
    setFinalizing(true)
    try {
      const { data } = await api.post('/papers', {
        title: title.trim(), venue: venue.trim(), sections: sectionsPayload(), versions,
      })
      message.success(`组卷成功：${data.question_count} 题，满分 ${data.total_score} 分`)
      setPreview({ title: title.trim(), data: data.preview })  // 定稿后直接弹预览
      window.open(data.download_url, '_blank')
      setSections(null)
      load()
    } finally { setFinalizing(false) }
  }

  const openHistoryPreview = async (id: number, t: string) => {
    const { data } = await api.get(`/papers/${id}`)
    setPreview({ title: t, data: data.preview })
  }

  const draftScore = (sections ?? []).reduce((s, sec) => s + sec.questions.reduce((a, q) => a + q.score, 0), 0)
  const draftCount = (sections ?? []).reduce((s, sec) => s + sec.questions.length, 0)

  return (
    <div>
      <Typography.Title level={3}>试卷组卷</Typography.Title>
      <Card title="① 组卷条件" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 12 }} wrap>
          <Input placeholder="试卷标题，如：葫芦岛移动分公司职级调整考试" value={title}
            onChange={(e) => setTitle(e.target.value)} style={{ width: 380 }} />
          <Input placeholder="考场名（可选），如：第三考场" value={venue}
            onChange={(e) => setVenue(e.target.value)} style={{ width: 200 }} />
        </Space>
        {criteria.map((c, i) => {
          const catKey = c.category === 'any' ? 'any' : c.category
          const avail = stock[c.q_type]?.[catKey] ?? 0
          return (
            <Space key={i} style={{ display: 'flex', marginBottom: 8 }} wrap>
              <Select value={c.q_type} style={{ width: 100 }}
                options={Object.entries(Q_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))}
                onChange={(v) => setRow(i, { q_type: v })} />
              <Select value={c.category} style={{ width: 120 }}
                options={[{ value: 'any', label: '不限大类' }, ...categories.map((x) => ({ value: x, label: x }))]}
                onChange={(v) => setRow(i, { category: v })} />
              <Select value={c.difficulty} style={{ width: 90 }} options={DIFF_OPTIONS}
                onChange={(v) => setRow(i, { difficulty: v })} />
              <InputNumber min={1} max={100} value={c.count} addonBefore="数量"
                onChange={(v) => setRow(i, { count: v ?? 1 })} style={{ width: 130 }} />
              <InputNumber min={1} max={100} value={c.score} addonBefore="分值"
                onChange={(v) => setRow(i, { score: v ?? 1 })} style={{ width: 130 }} />
              <Typography.Text type={avail < c.count ? 'danger' : 'secondary'}>
                可用 {avail} 道{avail < c.count && '（不足！）'}
              </Typography.Text>
              {criteria.length > 1 && (
                <Button size="small" icon={<DeleteOutlined />} danger
                  onClick={() => setCriteria(criteria.filter((_, j) => j !== i))} />
              )}
            </Space>
          )
        })}
        <Space style={{ marginTop: 8 }} wrap>
          <Button icon={<PlusOutlined />} onClick={() =>
            setCriteria([...criteria, { q_type: 'single', category: 'any', difficulty: 'any', count: 5, score: 1 }])}>
            加一行条件
          </Button>
          <Typography.Text strong>合计：{totalCount} 题 / 满分 {totalScore} 分</Typography.Text>
          <Radio.Group value={versions.length === 1 ? 'A' : 'AB'} optionType="button" buttonStyle="solid"
            onChange={(e) => setVersions(e.target.value === 'A' ? ['A'] : ['A', 'B'])}
            options={[{ value: 'A', label: '仅 A 卷' }, { value: 'AB', label: 'A、B 双卷' }]} />
          <Button type="primary" loading={drafting} onClick={makeDraft}>自动组卷（生成草稿）</Button>
        </Space>
      </Card>

      {sections && (
        <Card style={{ marginBottom: 16 }}
          title={<>② 草稿微调 <Typography.Text type="secondary" style={{ fontSize: 13 }}>
            （{draftCount} 题 / 满分 {draftScore} 分，可换题、删题后定稿）</Typography.Text></>}
          extra={<Space>
            <Button icon={<EyeOutlined />} loading={previewing} onClick={doPreview} disabled={draftCount === 0}>预览</Button>
            <Button type="primary" icon={<DownloadOutlined />} loading={finalizing}
              onClick={finalize} disabled={draftCount === 0}>
              定稿生成{versions.length === 1 ? ' A 卷' : ' AB 卷'}
            </Button>
          </Space>}>
          <Space wrap style={{ marginBottom: 8 }}>
            <Typography.Text strong>大类分布：</Typography.Text>
            {Object.entries(draftCatSummary()).map(([k, n]) =>
              <Tag color="blue" key={k}>{k} × {n}</Tag>)}
          </Space>
          {sections.map((sec, si) => (
            <div key={sec.q_type}>
              <Divider titlePlacement="start" style={{ margin: '12px 0 8px' }}>
                {sec.label}（{sec.questions.length} 题）
              </Divider>
              <List
                size="small" dataSource={sec.questions}
                renderItem={(q, qi) => (
                  <List.Item actions={[
                    <Button size="small" icon={<SwapOutlined />} onClick={() => openSwap(si, qi)}>换题</Button>,
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeQ(si, qi)} />,
                  ]}>
                    <Space size={4} style={{ flex: 1 }}>
                      <Tag>{q.category || '未分类'}</Tag>
                      <Typography.Text ellipsis style={{ maxWidth: 620 }}>
                        {qi + 1}. {q.stem}
                      </Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            </div>
          ))}
        </Card>
      )}

      <Card title="历史组卷">
        <Table<PaperRow>
          rowKey="id" dataSource={papers} size="small" pagination={false}
          expandable={{
            expandedRowRender: (p) => (
              <Space wrap style={{ paddingLeft: 12 }}>
                <Typography.Text type="secondary">单独下载 docx（便于微调）：</Typography.Text>
                {(p.files || []).map((f) => (
                  <Button key={f} size="small" icon={<DownloadOutlined />}
                    onClick={() => window.open(`/api/v1/papers/${p.id}/file?name=${encodeURIComponent(f)}`, '_blank')}>
                    {f.replace(`_${p.title}.docx`, '').replace('.docx', '')}
                  </Button>
                ))}
              </Space>
            ),
          }}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 55 },
            { title: '标题', dataIndex: 'title' },
            { title: '考场', dataIndex: 'venue', width: 90 },
            { title: '卷别', width: 80, render: (_, p) => (p.versions || []).join('、') },
            {
              title: '大类分布', width: 200,
              render: (_, p) => Object.entries(p.category_distribution || {})
                .map(([k, n]) => `${k}×${n}`).join('、') || '-',
            },
            { title: '题数', dataIndex: 'question_count', width: 55 },
            { title: '满分', dataIndex: 'total_score', width: 55 },
            { title: '生成时间', dataIndex: 'created_at', width: 150, render: (t: string) => t?.replace('T', ' ').slice(0, 19) },
            {
              title: '操作', width: 150,
              render: (_, p) => (
                <Space size={4}>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => openHistoryPreview(p.id, p.title)}>预览</Button>
                  <Button size="small" type="primary" icon={<DownloadOutlined />}
                    onClick={() => window.open(p.download_url, '_blank')}>整包</Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal open={!!swapTarget} title="选择替换题目" footer={null} width={680}
        onCancel={() => setSwapTarget(null)}>
        {alts.length === 0
          ? <Empty description="没有更多同题型/同大类的可换题目" />
          : <List size="small" dataSource={alts} renderItem={(a) => (
              <List.Item actions={[<Button size="small" type="primary" onClick={() => doSwap(a)}>选用</Button>]}>
                <Space size={4}>
                  <Tag>{a.category || '未分类'}</Tag>
                  <Typography.Text ellipsis style={{ maxWidth: 480 }}>{a.stem}</Typography.Text>
                </Space>
              </List.Item>
            )} />}
      </Modal>

      <Drawer open={!!preview} width={720} onClose={() => setPreview(null)}
        title={preview ? `预览：${preview.title}` : '预览'}>
        {preview && (
          <Tabs items={Object.entries(preview.data).map(([ver, secs]) => ({
            key: ver, label: `${ver} 卷`,
            children: (
              <div>
                {secs.map((sec, si) => (
                  <div key={sec.q_type}>
                    <Typography.Title level={5} style={{ marginTop: si ? 16 : 0 }}>
                      {['一', '二', '三', '四', '五', '六'][si]}、{sec.label}
                      （{sec.per_score ? `每题${sec.per_score}分，` : ''}共{sec.total}分）
                    </Typography.Title>
                    {sec.questions.map((q) => (
                      <div key={q.no} style={{ marginBottom: 10 }}>
                        <div>{q.no}. {q.stem}</div>
                        {q.options?.map((o) => (
                          <div key={o.key} style={{ paddingLeft: 18 }}>{o.key}. {o.text}</div>
                        ))}
                        <div style={{ color: 'var(--ths-accent, #c41d7f)', fontSize: 13 }}>
                          【答案】{sec.q_type === 'judge' ? (q.answer === 'A' ? '正确' : '错误') : q.answer}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ),
          }))} />
        )}
      </Drawer>
    </div>
  )
}
