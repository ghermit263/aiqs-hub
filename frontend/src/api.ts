import axios from 'axios'
import { message } from 'antd'

export const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      if (location.pathname !== '/login') location.href = '/login'
    } else {
      message.error(err.response?.data?.detail ?? err.message)
    }
    return Promise.reject(err)
  },
)

export const Q_TYPE_LABELS: Record<string, string> = {
  single: '单选题',
  multiple: '多选题',
  judge: '判断题',
  fill_blank: '填空题',
  short_answer: '简答题',
  essay: '论述题',
}

export const STATUS_LABELS: Record<string, string> = {
  pending_review: '待审核',
  approved: '已通过',
  rejected: '已退回',
  disabled: '已停用',
}

export const DIFFICULTY_LABELS: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

export interface Question {
  id: number
  q_type: string
  stem: string
  options: { key: string; text: string }[] | null
  answer: string
  analysis: string
  difficulty: string
  category: string
  subcategory: string
  tags: string
  status: string
  reject_reason: string | null
  document_id: number | null
  chunk_id: number | null
}

// 分类清单由后端 /categories 提供，这里仅作兜底默认
export const DEFAULT_CATEGORIES = ['战略', '党建廉洁', '内部知识', '管理', '企业文化', '智转数改']

export interface Doc {
  id: number
  filename: string
  file_type: string
  file_size: number
  parse_status: string
  parse_error: string | null
  chunk_count: number
  created_at: string
}

export interface Task {
  id: number
  document_id: number
  config: { type_counts: Record<string, number>; difficulty: string }
  model_name: string
  status: string
  error_msg: string | null
  question_count: number
  created_at: string
}
