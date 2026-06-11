import { useCallback, useEffect, useState } from 'react'
import { Button, Input, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { DownloadOutlined, TagsOutlined } from '@ant-design/icons'
import { DEFAULT_CATEGORIES, DIFFICULTY_LABELS, Q_TYPE_LABELS, api, type Question } from '../api'

export default function Bank() {
  const [items, setItems] = useState<Question[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [typeFilter, setTypeFilter] = useState<string>()
  const [categoryFilter, setCategoryFilter] = useState<string>()
  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES)
  const [subMap, setSubMap] = useState<Record<string, string[]>>({})
  const [keyword, setKeyword] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  // 改分类弹窗：ids 为待改题目（单题或批量），cat/sub 为目标分类
  const [catModal, setCatModal] = useState<{ ids: number[]; category?: string; subcategory: string } | null>(null)
  const canExport = localStorage.getItem('role') !== 'uploader'
  const canEdit = localStorage.getItem('role') !== 'uploader'

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/questions', {
        params: { status: 'approved', q_type: typeFilter, category: categoryFilter,
                  keyword: keyword || undefined, page, page_size: 20 },
      })
      setItems(data.items); setTotal(data.total)
    } finally { setLoading(false) }
  }, [typeFilter, categoryFilter, keyword, page])

  useEffect(() => {
    api.get('/categories').then((r) => { setCategories(r.data.categories); setSubMap(r.data.subcategories) })
  }, [])

  useEffect(() => { load() }, [load])

  const applyCategory = async () => {
    if (!catModal) return
    await api.post('/questions/batch-category', {
      ids: catModal.ids, category: catModal.category ?? '', subcategory: catModal.subcategory ?? '',
    })
    message.success(`已更新 ${catModal.ids.length} 题的分类`)
    setCatModal(null); setSelected([]); load()
  }

  const doExport = async () => {
    const body = selected.length
      ? { ids: selected }
      : { q_types: typeFilter ? [typeFilter] : undefined, keyword: keyword || undefined }
    const { data } = await api.post('/exports', body)
    message.success(`已导出 ${data.question_count} 题`)
    window.open(data.download_url, '_blank')
  }

  return (
    <div>
      <Typography.Title level={3}>标准题库 <Typography.Text type="secondary" style={{ fontSize: 14 }}>共 {total} 题</Typography.Text></Typography.Title>
      <Space style={{ marginBottom: 12 }}>
        <Select value={typeFilter} onChange={(v) => { setTypeFilter(v); setPage(1) }} allowClear placeholder="全部题型" style={{ width: 130 }}
          options={Object.entries(Q_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
        <Select value={categoryFilter} onChange={(v) => { setCategoryFilter(v); setPage(1) }} allowClear placeholder="全部大类" style={{ width: 130 }}
          options={categories.map((c) => ({ value: c, label: c }))} />
        <Input.Search placeholder="搜索题干/答案" allowClear style={{ width: 240 }}
          onSearch={(v) => { setKeyword(v); setPage(1) }} />
        {canEdit && (
          <Button icon={<TagsOutlined />} disabled={!selected.length}
            onClick={() => setCatModal({ ids: selected, category: undefined, subcategory: '' })}>
            批量改分类{selected.length ? `（${selected.length}）` : ''}
          </Button>
        )}
        {canExport && (
          <Button type="primary" icon={<DownloadOutlined />} onClick={doExport} disabled={total === 0}>
            {selected.length ? `导出选中 ${selected.length} 题` : '导出当前筛选结果'}
          </Button>
        )}
      </Space>
      <Table<Question>
        rowKey="id" dataSource={items} loading={loading} size="middle"
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage, showTotal: (t) => `共 ${t} 题` }}
        expandable={{
          expandedRowRender: (q) => (
            <div style={{ paddingLeft: 24 }}>
              {q.options?.map((o) => <div key={o.key}>{o.key}. {o.text}</div>)}
              <div><b>答案：</b>{q.answer}</div>
              {q.analysis && <div><b>解析：</b>{q.analysis}</div>}
            </div>
          ),
        }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 70 },
          { title: '题型', dataIndex: 'q_type', width: 90, render: (t: string) => <Tag>{Q_TYPE_LABELS[t]}</Tag> },
          {
            title: '分类', width: 150,
            render: (_, q) => q.category
              ? <Tag color="blue">{q.category}{q.subcategory ? ` / ${q.subcategory}` : ''}</Tag>
              : <Tag>未分类</Tag>,
          },
          { title: '题干', dataIndex: 'stem', ellipsis: true },
          { title: '难度', dataIndex: 'difficulty', width: 80, render: (d: string) => DIFFICULTY_LABELS[d] },
          ...(canEdit ? [{
            title: '操作', width: 90,
            render: (_: unknown, q: Question) => (
              <Button size="small" onClick={() =>
                setCatModal({ ids: [q.id], category: q.category || undefined, subcategory: q.subcategory })}>
                改分类
              </Button>
            ),
          }] : []),
        ]}
      />
      <Modal open={!!catModal} title={catModal && catModal.ids.length > 1 ? `批量修正 ${catModal.ids.length} 题的分类` : '修正分类'}
        onOk={applyCategory} onCancel={() => setCatModal(null)} okText="保存">
        {catModal && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Typography.Text>大类</Typography.Text>
              <Select allowClear placeholder="未分类（清空）" style={{ width: '100%' }} value={catModal.category}
                onChange={(v) => setCatModal({ ...catModal, category: v, subcategory: '' })}
                options={categories.map((c) => ({ value: c, label: c }))} />
            </div>
            <div>
              <Typography.Text>小类（可空）</Typography.Text>
              <Select allowClear showSearch mode="tags" maxCount={1} placeholder="可填可选" style={{ width: '100%' }}
                value={catModal.subcategory ? [catModal.subcategory] : []}
                onChange={(v) => setCatModal({ ...catModal, subcategory: (v as string[])[0] ?? '' })}
                options={(subMap[catModal.category ?? ''] ?? []).map((s) => ({ value: s, label: s }))} />
            </div>
          </Space>
        )}
      </Modal>
    </div>
  )
}
