import { theme as antdTheme, type ThemeConfig } from 'antd'

export type SkinKey = 'terminal' | 'tang' | 'song'

export interface Skin {
  key: SkinKey
  label: string
  hint: string
  isDark: boolean
  menuTheme: 'dark' | 'light'
  antd: ThemeConfig
  /** 注入 :root 的 CSS 变量，供自定义元素（背景、代码块、侧栏、滚动条等）使用 */
  vars: Record<string, string>
}

// ---------------- 终端风：荧光绿 / 炭黑 ----------------
const terminal: Skin = {
  key: 'terminal',
  label: '终端风',
  hint: '荧光绿 · 炭黑',
  isDark: true,
  menuTheme: 'dark',
  antd: {
    algorithm: antdTheme.darkAlgorithm,
    token: {
      colorPrimary: '#39ff14',
      colorInfo: '#39ff14',
      colorSuccess: '#46f08a',
      colorWarning: '#e3ff5c',
      colorError: '#ff5c5c',
      colorBgBase: '#0a0e0a',
      colorTextBase: '#c8facc',
      colorLink: '#5cff8f',
      fontFamily: "'Cascadia Code', 'Consolas', 'JetBrains Mono', 'Courier New', monospace",
      borderRadius: 2,
      wireframe: true,
    },
    components: {
      Layout: { siderBg: '#070b07', headerBg: '#070b07', bodyBg: '#0a0e0a' },
      Menu: { darkItemBg: '#070b07', darkItemSelectedBg: '#11401a', darkItemColor: '#7fdc91' },
      Card: { colorBgContainer: '#0e140e' },
      Table: { colorBgContainer: '#0e140e', headerBg: '#111811' },
    },
  },
  vars: {
    '--ths-bg': '#0a0e0a',
    '--ths-panel': '#0e140e',
    '--ths-text': '#c8facc',
    '--ths-muted': '#6f9c79',
    '--ths-accent': '#39ff14',
    '--ths-border': '#1d3a1d',
    '--ths-sider-bg': '#070b07',
    '--ths-sider-title': '#39ff14',
    '--ths-code-bg': '#050805',
    '--ths-code-text': '#8cff9e',
    '--ths-code-keyword': '#39ff14',
    '--ths-login-bg': 'radial-gradient(circle at 50% 30%, #10210f 0%, #050805 70%)',
    '--ths-scrollbar': '#1d3a1d',
  },
}

// ---------------- 唐风：绛红 / 赭黄 / 石青，华丽大气 ----------------
const tang: Skin = {
  key: 'tang',
  label: '唐风',
  hint: '绛红 · 赭黄 · 石青',
  isDark: false,
  menuTheme: 'dark',
  antd: {
    algorithm: antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: '#8c1f28',   // 绛红
      colorInfo: '#2e6e8e',      // 石青
      colorWarning: '#c9962e',   // 赭黄
      colorSuccess: '#5a7d4f',
      colorError: '#a8202a',
      colorBgBase: '#f7ecd6',
      colorTextBase: '#3a261f',
      colorLink: '#2e6e8e',
      fontFamily: "'STKaiti', 'KaiTi', '楷体', 'Noto Serif SC', serif",
      borderRadius: 6,
    },
    components: {
      Layout: { siderBg: '#6e1620', headerBg: '#f7ecd6', bodyBg: '#f3e3c4' },
      Menu: {
        darkItemBg: '#6e1620', darkSubMenuItemBg: '#5a1019',
        darkItemSelectedBg: '#c9962e', darkItemSelectedColor: '#3a261f',
        darkItemColor: '#f0d9b5',
      },
      Card: { colorBgContainer: '#fcf6e9', headerBg: '#f3e3c4' },
      Table: { headerBg: '#f0e0c0', colorBgContainer: '#fcf6e9' },
      Button: { defaultBorderColor: '#c9962e' },
    },
  },
  vars: {
    '--ths-bg': '#f3e3c4',
    '--ths-panel': '#fcf6e9',
    '--ths-text': '#3a261f',
    '--ths-muted': '#8a6a4a',
    '--ths-accent': '#2e6e8e',
    '--ths-border': '#d8b98a',
    '--ths-sider-bg': '#6e1620',
    '--ths-sider-title': '#f0d9b5',
    '--ths-code-bg': '#fbf0d8',
    '--ths-code-text': '#5a1019',
    '--ths-code-keyword': '#8c1f28',
    '--ths-login-bg': 'linear-gradient(135deg, #8c1f28 0%, #c9962e 100%)',
    '--ths-scrollbar': '#d8b98a',
  },
}

// ---------------- 宋风：青灰 / 米白 / 茶褐，素雅留白 ----------------
const song: Skin = {
  key: 'song',
  label: '宋风',
  hint: '青灰 · 米白 · 茶褐',
  isDark: false,
  menuTheme: 'light',
  antd: {
    algorithm: antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: '#5c6b73',   // 青灰
      colorInfo: '#5c6b73',
      colorWarning: '#a98b5d',
      colorSuccess: '#6e8b6e',
      colorError: '#9c5a4a',
      colorBgBase: '#f5f1e8',    // 米白
      colorTextBase: '#4a3b2e',  // 茶褐
      colorLink: '#5c6b73',
      fontFamily: "'Songti SC', 'STSong', 'SimSun', '宋体', 'Noto Serif SC', serif",
      borderRadius: 2,
      paddingLG: 28,
    },
    components: {
      Layout: { siderBg: '#e9e3d5', headerBg: '#f5f1e8', bodyBg: '#f5f1e8' },
      Menu: {
        itemBg: '#e9e3d5', itemSelectedBg: '#d6cdb8', itemSelectedColor: '#4a3b2e',
        itemColor: '#6b5444',
      },
      Card: { colorBgContainer: '#fbf9f3', headerBg: '#f1ece0' },
      Table: { headerBg: '#efe9dc', colorBgContainer: '#fbf9f3' },
    },
  },
  vars: {
    '--ths-bg': '#f5f1e8',
    '--ths-panel': '#fbf9f3',
    '--ths-text': '#4a3b2e',
    '--ths-muted': '#8a7a68',
    '--ths-accent': '#6b5444',
    '--ths-border': '#ddd3c0',
    '--ths-sider-bg': '#e9e3d5',
    '--ths-sider-title': '#4a3b2e',
    '--ths-code-bg': '#f1ece0',
    '--ths-code-text': '#6b5444',
    '--ths-code-keyword': '#5c6b73',
    '--ths-login-bg': 'linear-gradient(160deg, #f5f1e8 0%, #e3dccb 100%)',
    '--ths-scrollbar': '#ddd3c0',
  },
}

export const SKINS: Record<SkinKey, Skin> = { terminal, tang, song }
export const SKIN_ORDER: SkinKey[] = ['terminal', 'tang', 'song']

export function loadSkin(): SkinKey {
  const s = localStorage.getItem('skin') as SkinKey | null
  return s && SKINS[s] ? s : 'song'
}
